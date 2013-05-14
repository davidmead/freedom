freedom.io
==========

Sets free your Facebook, Twitter, and Google+ posts by copying them to your WordPress blog via XML-RPC, with all formatting and details intact.

Social networks keep your memories locked up. Take them back and set them free! Copy your posts, pictures, and other content to a blog of your choice.

License: This project is placed in the public domain.


Development
===========

Requirements:

- Python 2.7
- Google App Engine (either dev_appserver or prod), which includes:
  - django
  - mox (for tests)
  - webob
  - yaml
- Libraries in git submodules (be sure to run git submodule init and git
  submodule update!):
  - http://github.com/snarfed/activitystreams-unofficial
  - http://github.com/musicmetric/google-api-python-client
  - http://github.com/adamjmcgrath/httplib2
  - http://github.com/wishabi/python-gflags
  - http://github.com/michaelhelmick/python-tumblpy
  - http://github.com/kennethreitz/requests
  - http://github.com/requests/requests-oauthlib
  - http://github.com/idan/oauthlib
  - http://github.com/snarfed/gdata-python-client


TODO
====
- migration page
- pause/resume/cancel migration
- posthaven
- finish post/comment processing for:
  - facebook
  - twitter
  - g+
- make tasks transactional where necessary
- port to ndb?
