"""Model base classes.
"""

__author__ = ['Ryan Barrett <freedom@ryanb.org>']

import datetime
import itertools
import json
import logging
import urlparse

import appengine_config
from webutil import util
from webutil import webapp2

from google.appengine.api import taskqueue
from google.appengine.ext import db


class SpaceKeyNameModel(util.KeyNameModel):
  """A model class with a key name of multiple strings separated by spaces.

  The component strings themselves must not have spaces in them.
  """

  def __init__(self, *args, **kwargs):
    """Sets key_name using the string components in the positional args.

    'key_name' must not be in kwargs.
    """
    if args and args[0]:
      assert 'key_name' not in kwargs
      kwargs['key_name'] = self.make_key_name(args)
    super(SpaceKeyNameModel, self).__init__(**kwargs)

  # this doesn't work because it uses the bound class name for the
  # inner get_or_insert() call as the kind.
  #
  # @classmethod
  # def get_or_insert(cls, *args, **kwargs):
  #   """Wraps get_or_insert() and constructs a key name from positional args."""
  #   return .get_or_insert(
  #       SpaceKeyNameModel.make_key_name(*args), **kwargs)

  @staticmethod
  def make_key_name(*args):
    """Makes and returns a key name from the given component strings."""
    for part in args:
      assert ' ' not in part
    return ' '.join(args)

  def key_name_parts(self):
    """Returns the key name component strings as a list."""
    return self.key().name().split(' ')

  # @db.transactional
  # def get_or_save(self):
  #   existing = db.get(self.key())
  #   if existing:
  #     logging.debug('Deferring to existing %s entity: %s',
  #                   self.kind(), self.key_name())
  #     return existing

  #   logging.debug('New entity to propagate: %s', key_str)
  #   taskqueue.add(queue_name='propagate', params={'key': str(self.key())})
  #   self.save()
  #   return self


class Source(SpaceKeyNameModel):
  """A source to read posts from, e.g. a Facebook profile.

  Each concrete source type should subclass this.
  """

  # POLL_TASK_DATETIME_FORMAT = '%Y-%m-%d-%H-%M-%S'
  # EPOCH = datetime.datetime.utcfromtimestamp(0)
  # last_polled = db.DateTimeProperty(default=EPOCH)

  # human-readable name for this source type. subclasses should override.
  TYPE_NAME = None

  url = db.LinkProperty()
  picture = db.LinkProperty()

  @classmethod
  def create_new(cls, handler, **kwargs):
    """Creates and saves a new Source and adds a poll task for it.

    Args:
      handler: the current webapp.RequestHandler
      **kwargs: passed to new()
    """
    new = cls.new(handler, **kwargs)
    new.save()
    new.add_scan_task()
    return new

  @classmethod
  def new(cls, handler, **kwargs):
    """Factory method. Creates and returns a new instance for the current user.

    To be implemented by subclasses.

    Args:
      handler: the current webapp.RequestHandler
      **kwargs: passed to new()
    """
    raise NotImplementedError()

  def display_name(self):
    """Returns a human-readable name for this source, e.g. 'My Thoughts'.

    To be implemented by subclasses.
    """
    raise NotImplementedError()

  def type_display_name(self):
    """Returns a human-readable name for this type of source, e.g. 'Facebook'.

    To be implemented by subclasses.
    """
    raise NotImplementedError()

  def get_posts(self, scan_url):
    """Fetches a page of Post instances using the given source API URL.

    To be implemented by subclasses.

    Args:
      scan_url: string, the source API URL to fetch the current page of posts

    Returns:
      (posts, next_scan_url). post is a sequence of Migratable instances,
      next_scan_url is a string, the source API URL to use for the next scan, or
      None if there are no more posts.
    """
    raise NotImplementedError()


class Destination(SpaceKeyNameModel):
  """A web site to propagate posts to, e.g. a WordPress blog.

  Each concrete destination class should subclass this class.
  """

  last_updated = db.DateTimeProperty()

  def add_comment(self, comment):
    """Posts the given comment to this site.

    To be implemented by subclasses.

    Args:
      comment: Comment
    """
    raise NotImplementedError()


class Migration(SpaceKeyNameModel):
  """A migration from a single source to a single destination.

  Key name is 'SOURCE_KIND SOURCE_KEY_NAME DEST_KIND DEST_KEY_NAME', e.g.
  'Facebook 123 Wordpress http://snarfed.org/w/_0'. The four components must not
  have spaces in them.
  """

  STATUSES = ('new', 'processing', 'complete')
  status = db.StringProperty(choices=STATUSES, default='new')
  id = db.IntegerProperty(required=True)

  def source(self):
    """Returns this Migration's source."""
    logging.info('Getting source %s', self.key_name_parts()[:2])
    return db.get(db.Key.from_path(*self.key_name_parts()[:2]))

  def dest(self):
    """Returns this Migration's destination."""
    logging.info('Getting dest %s', self.key_name_parts()[2:])
    return db.get(db.Key.from_path(*self.key_name_parts()[2:]))


class Migratable(SpaceKeyNameModel):
  """A post or comment to be migrated.

  The key name is 'ID MIGRATION_KEY_NAME', where ID is the source-specific id of
  the post or comment and must not have spaces in it.
  """

  STATUSES = ('new', 'processing', 'complete')

  status = db.StringProperty(choices=STATUSES, default='new')
  leased_until = db.DateTimeProperty()
  # JSON data for this post from the source social network's API.
  data = db.StringProperty()

  def propagate(self):
    """Propagates this post or comment to its destination.

    To be implemented by subclasses.
    """
    raise NotImplementedError()

  @db.transactional
  def get_or_save(self):
    existing = db.get(self.key())
    key_str = '%s %s' % (self.kind(), self.key().name())
    if existing:
      logging.debug('Deferring to existing entity: %s', key_str)
      return existing

    logging.debug('New entity to propagate: %s', key_str)
    taskqueue.add(queue_name='propagate', params={'key': str(self.key())})
    self.save()
    return self

  def id(self):
    """Returns this post's id."""
    return self.key_name_parts()[0]

  def dest(self):
    """Returns the destination for this post's migration."""
    return db.get(*self.key_name_parts()[3:])
