# Contributing to IBeam

We'd love for you to contribute to our source code and to make IBeam even better than it is today! Here are the guidelines we'd like you to follow:

 - [Code of Conduct](#coc)
 - [Question or Problem?](#question)
 - [Issues and Bugs](#issue)
 - [Submission Guidelines](#submit)
 - [Coding Rules](#rules)

## <a name="coc"></a> Code of Conduct

As contributors and maintainers of the IBeam project, we pledge to respect everyone who contributes by posting issues, updating documentation, submitting pull requests, providing feedback in comments, and any other activities.

Communication within our community must be constructive and never resort to personal attacks, trolling, public or private harassment, insults, or other unprofessional conduct.

We promise to extend courtesy and respect to everyone involved in this project regardless of gender, gender identity, sexual orientation, disability, age, race, ethnicity, religion, or level of experience. We expect anyone contributing to the project to do the same.

If any member of the community violates this code of conduct, the maintainers of IBeam may take action, removing issues, comments, and PRs or blocking accounts as deemed appropriate.

If you are subject to or witness unacceptable behavior, or have any other concerns, please drop us a line at [voy1982@yahoo.co.uk][voy1982_email]

## <a name="question"></a> Got a Question or Problem?

If you have questions about how to use IBeam, please direct these to [StackOverflow][stackoverflow] and use the `ibeam` tag. We are also available on [GitHub issues][github].

If you feel that we're missing an important bit of documentation, feel free to
file an issue so we can help. Here's an example to get you started:

```
What are you trying to do or find out more about?

Where have you looked?

Where did you expect to find this information?
```

## <a name="issue"></a> Found an Issue?
If you find a bug in the source code, you can help us by submitting an issue to our [GitHub Repository][github]. Even better you can submit a Pull Request with a fix.

See [below](#submit) for some guidelines.

## <a name="submit"></a> Submission Guidelines

### Submitting an Issue
Before you submit your issue search the archive, maybe your question was already answered.

If your issue appears to be a bug, and hasn't been reported, open a new issue.
Help us to maximize the effort we can spend fixing issues and adding new
features, by not reporting duplicate issues.

Here's a template to get you started:

```
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment**
IBeam version:
Python version:
OS:

**Additional context**
Add any other context about the problem here.

**Suggest a Fix**
If you can't fix the bug yourself, perhaps you can point to what might be causing the problem (line of code or commit).

```

### Submitting a Pull Request
Before you submit your pull request consider the following guidelines:

* Search [GitHub](https://github.com/Voyz/ibeam/pulls) for an open or closed Pull Request
  that relates to your submission. You don't want to duplicate effort.
* Make your changes in a new git branch, based off master branch:

     ```shell
     git checkout -b my-fix-branch master
     ```

* Create your patch, **including appropriate test cases**.
* Follow our [Coding Rules](#rules).
* Avoid checking in files that shouldn't be tracked (e.g `dist`, `build`, `.tmp`, `.idea`). We recommend using a [global](#global-gitignore) gitignore for this.
* Commit your changes using a descriptive commit message.

     ```shell
     git commit -a
     ```
  Note: the optional commit `-a` command line option will automatically "add" and "rm" edited files.

* Push your branch to GitHub:

    ```shell
    git push origin my-fix-branch
    ```

* In GitHub, send a pull request to `ibeam:master`.
* If we suggest changes then:
  * Make the required updates.
  * Rebase your branch and force push to your GitHub repository (this will update your Pull Request):

    ```shell
    git rebase master -i
    git push origin my-fix-branch -f
    ```

That's it! Thank you for your contribution!

#### After your pull request is merged

After your pull request is merged, you can safely delete your branch and pull the changes
from the main (upstream) repository:

* Delete the remote branch on GitHub either through the GitHub web UI or your local shell as follows:

    ```shell
    git push origin --delete my-fix-branch
    ```

* Check out the master branch:

    ```shell
    git checkout master -f
    ```

* Delete the local branch:

    ```shell
    git branch -D my-fix-branch
    ```

* Update your master with the latest upstream version:

    ```shell
    git pull --ff upstream master
    ```

## <a name="rules"></a> Coding Rules

We generally follow the [Google Python style guide][py-style-guide].

----

*This guide was inspired by the [Firebase Web Quickstarts contribution guidelines](https://github.com/firebase/quickstart-js/blob/master/CONTRIBUTING.md).*

[github]: https://github.com/Voyz/ibeam
[py-style-guide]: http://google.github.io/styleguide/pyguide.html
[jsbin]: http://jsbin.com/
[stackoverflow]: http://stackoverflow.com/questions/tagged/ibeam
[global-gitignore]: https://help.github.com/articles/ignoring-files/#create-a-global-gitignore
[voy1982_email]: mailto://voy1982@yahoo.co.uk