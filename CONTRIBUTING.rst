First things first: No questions in the issue tracker please. Spyne
maintainers answer questions in the Spyne mailing list
( https://lists.spyne.io/lists/people ) or StackOverflow questions
tagged ``[spyne]`` (https://stackoverflow.com/questions/tagged/spyne).
Questions filed in the issue tracker get closed without being looked at.

If you are not here to ask a question, please read on.

--------------------------------

Hey there! Thanks a lot for considering to contribute to Spyne! Here are some
things you might want to know.

Do you actually need your code in Spyne?
========================================

Spyne code is highly modular. If you are adding a new transport, protocol, or
model type, you might want to keep the code in a separate package. This will
make it possible to work at your own pace, use your own code style, your own
licensing terms, etc.

However, if:

- You are fixing a bug in Spyne
- Your code is tightly coupled with Spyne (i.e. it's using private APIs,
  needs monkey-patching to work outside of Spyne, etc.)
- You are adding a new feature to a partly-finished part of Spyne
- You are not sure

... just send a pull request and we will talk.

Spyne development guidelines
============================

If you wish to contribute to Spyne's development, start by creating a personal
fork on GitHub. When you are ready to push to the upstream repository,
submit a pull request to bring your work to the attention of the core
committers. They will respond to review your patch and act accordingly.

Code format
-----------

The only hard rule we have is to avoid tests in code (you are supposed to put
all tests in the ``spyne.tests`` package). A test is a member function of a
`TestSomething` class inside a module from ``spyne.tests`` package.

This means eg. no doctests, no `if __name__ == '__main__'` etc. Spyne's test
infrastructure is complex enough as it is and we won't complicate it any further
for your hippie testing tool-or-methodology-du-jour for no good reason.

That said, there are also a bunch of other guidelines that are mostly followed
by Spyne code. They are not really mandatory for your pull request to go in but
a consistent code style *does* make the lives of the future generations much
easier.

They are, in no particular order:

-   Use stair-style indentation for long lines. E.g.

    ::

        this_is_the_result_of = a_function_with_a_very_long_name(
                   that_takes, a_lot_of, arguments.that_have,
                        long_yet_informative_names, which_makes_the_code,
                              a_pleasure_to_read, yet_sometimes_a_pain_to_write)

    where the rightmost character of the last line is ALWAYS on the 80th column.

-   Every module starts with:

     1. Hashbang line (only if executable)
     2. ``# encoding: utf8`` line or empty line.
     3. Spyne license header. Leading and trailing lines with just ``#`` in them
        look nice.
     4. Future imports (if needed)
     5. Logger set up, i.e.:

        ::

            import logging
            logger = logging.getLogger(__name__)

        This is needed to catch any import-level logging.

     6. Preferred order for import statements is as follows:

        - stdlib absolute imports
        - other absolute imports (grouped by package)
        - stdlib relative imports
        - other relative imports (grouped by package)

-   When in doubt, follow `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_

Have fun!

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

Miscellanous Remarks
--------------------

* When overriding a method in a class use the ``super()`` to call the parent
  implementation instead of explicitly specifying the parent class. Not only
  this is mandatory for Python 3 compatibility, but also it's needed to
  correctly call all implementations of the overridden method according to MRO
  in cases of multiple inheritance.

* Unit tests should test the root functionality as closely as possible.
  This way, instead of getting a less useful "something broke" alert, we'd get
  e.g. "something broke in the validation of customized types used as xml
  attributes" alert.
