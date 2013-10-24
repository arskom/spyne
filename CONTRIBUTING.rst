
Spyne development guidelines
============================

If you wish to contribute to Spyne's development, create a personal fork
on GitHub. When you are ready to push to the upstream repository,
submit a pull request to bring your work to the attention of the core
committers. They will respond to review your patch and act accordingly.

Code format
-----------

Please follow the `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_
style guidelines for both source code and docstrings.

Branching
---------

For fixing an issue or adding a feature create a new branch from ``master``
branch.

Github's pull-request feature is awesome, but there's a subtlety that's not
totally obvious for newcomers: If you continue working on the branch that you
used to submit a pull request, your commits will "pollute" the pull request
until it gets merged. This is not a bug, but a feature -- it gives you the
ability to address reviewers' concerns without creating pull requests over and
over again. So, if you intend to work on other parts of spyne after submitting
a pull request, please do move your work to its own branch and never submit a
pull request from your master branch. This will give you the freedom to
continue working on Spyne while waiting for your pull request to be reviewed.

Pull requests
-------------

When submitting a pull request, make sure:

* Your commit messages are to-the-point and the actual patches are in line with
  the commit messages. Don't hesitate to push as many commits as possible. Git
  makes it very easy to split changes to relevant chunks once your work is done.
  You can either use ```git gui``` or ```git add -i``` -- they're a joy to work
  with once you get the hang of all this DVCS story.
* You have added tests for the feature you're adding or the bug you're fixing.
* You also have added short description of the changes in ``CHANGELOG.rst`` if
  you think it's needed.

Do note that we keep the master branch on the upstream repository "clean" --
i.e. we never merge pull requests with failing tests. So make sure all old and
new tests pass before submitting pull requests.

Regular contributors may be invited to join as a core Spyne committer on
GitHub. Even if this gives the core committers the power to commit directly
to the core repository, we highly value code reviews and expect every
significant change to be committed via pull requests.

Development principles
----------------------

* When overriding a method in a class use the ``super()`` to call the parent
  implementation instead of explicitly specifying the parent class. This is
  needed to correctly call all implementations of the overridden method
  according to MRO in cases of multiple inheritance.

* Unit tests should test the root functionality as closely as possible.
  This way, instead of getting a useless "something broke" alert, we'd get
  e.g. "something broke in the validation of customized types used as xml
  attributes" alert.
