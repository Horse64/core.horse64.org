
How to contribute
=================

This document explains how to contribute to Horse64.
If you want to help out then please read on.


Contribute testing feedback
---------------------------

If you want to help testing, [get the SDK](
/docs/Resources.md#sdk), play with it, and
[report bugs]( report-bugs). Here's a
[setup guide](/docs/Tutorials/Initial%20Setup.md).


Contribute code
---------------

If you want to contribute code to core tooling, please read:

1. For now, many tests expect to run *on Linux.* If you
   contribute a bigger feature, you'll need to test on
   Linux according to the [checklists](#maintainer-checklists).
   It's possible to do basic tests and changes on Windows if it's
   parts written in Horse64. It might be less practical for
   Horse64 Root.

2. [Read the licensing carefully](/docs/Resources.md#license)
   and agree to contribute your code under the given terms.
   ⚠️ **We cannot accept any code that used AI-based code generation
   or code completion, like "Co-Pilot" etc., [see
   here](#why-ai-contributions-are-not-allowed)** ⚠️

3. Changes are done via **pull requests** in the
   [respective repositories](/docs/Resources.md).

   To set up a new pull request, try these steps (**warning**,
   you should know terminal basics like changing directories):

   1. Make an account on [codeberg.org](
      https://codeberg.org/):

      ![](Screenshot%20Codeberg%20Signup.png)

      Also, install [**git for Windows**](
      https://git-scm.com/download/win) and a text
      editor for editing code.

   2. Browse to the respective Horse64 project repository for
      whatever tool you want to patch on **Codeberg**.

   3. Click the "Fork" button on the codeberg page
      of the repository to get a personal fork, that's your own
      separate project copy:

      ![](Screenshot%20Codeberg%20Fork.png)

   4. Clone your personal fork to your local machine with:

      ```bash
      git clone ...url-to-your-repo-fork-on-codeberg...
      ```

      Run that in a terminal, on Windows use
      e.g. the **git cmd terminal** of [Git for Windows
      ](https://www.git-scm.com/download/win):
      
      ![](Screenshot%20Git%20Cmd.png)

      Then `cd` into the directory in your terminal and
      switch to a new branch:

      ```bash
      git checkout -b name-for-your-branch
      ```

   5. Implement and **test** your change.

   6. Make sure to set up a name and e-mail with your
      local git if you haven't yet:

      ```bash
      git config user.name "John Doe"
      git config user.email "my-mail@example.com"
      ```

   7. Now use:

      ```bash
      git commit -a
      ```
      ...to save and describe your changes
      to your local repository. Make sure to
      [add your developer certificiate of origin signature,
      see the license file](/docs/Resources.md#license).

      (If you added any new files, you might first
      need to use `git add name-of-file`.)

      Then use:

      ```bash
      git push origin name-for-your-branch
      ```
      ...to push your change to your personal fork online.

   8. Now go to the original repository on Codeberg, **not
      your fork**, go to "Pull Requests", and use
      "New Pull Request":

      ![](Screenshot%20Codeberg%20Pull%20Request.png)

      For the "merge into" setting, make
      sure it's set to the project's original "main" branch.
      For "pull from", pick your personal fork and your
      `name-for-your-branch` branch.

If you want to talk to other developers,
[join the 💬 community chat](https://horse64.org/chat).


Contribute documentation
------------------------

You can find the documentation, including this file itself,
in the [main repository of the core.horse64.org package](
/docs/Resources.md#standard-library), it's inside the `docs`
folder. Feel free to suggest improvements.
⚠️ **We cannot accept any text that used AI-based text generation
or suggestions, like "ChatGPT" etc., [see
here](#why-ai-contributions-are-not-allowed).** ⚠️


Contribute funding
------------------

This project **doesn't accept funding nor donations.**

- But [here is info on the key people
  ](https://horse64.org/who), if you wanted to cheer them
  on or to join their other ventures and activities.


Maintainer checklists
---------------------

These are maintainer checklists for all the core projects:

### Pull request checklist for core tooling

If you contribute a pull request... FIXME

### Updating git hooks or issue forms

Whenever updating the git hooks, or the forms in the `.gitea`
directory, or the workflows to disable pull requests in the
`.github` directory, update them in the core.horse64.org main
repository first.

Then run (in the main repository directory):
```bash
python3 maintainer-helper-update-repos.py
```
...to propagate the changes to all the other repository.

(The other repositories need to be cloned to neighboring
repository directories, neighboring your core.horse64.org
repository directory.)

### Update all copyright notices for the next year

To update all copyright notices for the next year,
do the same steps as for [updating the git hooks for
all repositories](#updating-git-hooks-or-issue-forms).

### Release checklist for core tooling

This release checklist should be completed before attempting
any release of what is part of the core tooling.

**What is part of the core tooling:** This list continuously
expands and is made up of what is needed to build *horp*,
*HVM*, and *the standard library*. **The authoritative latest
list for what is part of that, is maintained as part of
`tools/maintainer_helper_test_major_builds.h64` in
the [core.horse64.org main repository](
/docs/Resources.md#standard-library).**

**Steps required** before any official release of core tooling:

1. Be on Linux.

2. Set up the core tooling repository directories next to
   each other in the versions to be tested, including what
   you plan to release.

3. Run this and follow the instructions:

   ```bash
   translator/horsec_run.py tools/maintainer_helper_test_major_builds.h64
   ```

   (Run it in the core.horse64.org **even if your change is in a
   different package.)**

4. If it reports an error at any point, it should be fixed
   before a release.

5. Now you should run whatever tests the respective
   project or package offers. For HVM, that would usually be
   `make test`, and for the others that would usually be via
   `horp test`. If there are any errors, make sure to investigate
   if any are new!


Why AI contributions are not allowed
------------------------------------

For legal reasons, **we absolutely cannot accept any AI
contributions** since it would put the Horse64 ecosystem
into untenable uncertainty.

To avoid legal risks, Horse64's **DCO** requires you to state
you made the contribution and can guarantee it's not plagiarized
whenever you contribute. But with the legal situation around AI,
many industry analysists are convinced this isn't possible with
AI output. [See this article for a more in-depth
explanation, including other reasons like quality
control](https://www.theregister.com/2024/04/16/gentoo_linux_ai_ban/).

Until this situation is more cleared up, we therefore cannot
risk any AI contributions. Please **don't under any circumstances**
submit code or text that was in full or even in part written by AI.


