# Style
*A brief, human- and agent-friendly introduction to repository style conventions.*

To read about deterministic formatting and linting, see [DEVTOOLS.md](DEVTOOLS.md).

## Files and Folders

- Whitespace is prohibited in folder or file names

## Python Code Style

### Use NumPy-Style Docstrings

Follow [NumPy style guidelines](https://numpydoc.readthedocs.io/en/latest/format.html)
when writing docstrings. You may [configure PyCharm](https://www.jetbrains.com/help/pycharm/settings-tools-python-integrated-tools.html) 
to use numpy-style docstrings.

**Keep docstrings concise**. Prefer a one-liner when the function name 
and type hints are self-explanatory.

**Examples:**

```python
# ✅ Good - concise, types speak for themselves
def get_user_by_id(user_id: str) -> User | None:
    """Fetch user from database by ID."""


# ❌ Avoid - bloated docstring for simple function
def get_user_by_id(user_id: str) -> User | None:
    """Get a user by their ID.

    Parameters
    ----------
    user_id : str
        The ID of the user to fetch.

    Returns
    -------
    User | None
        The user if found, None otherwise.
    """


# ✅ Good - complex function warrants full docstring
def calculate_metrics(data: list[float], threshold: float) -> dict[str, float]:
    """Calculate statistical metrics for the given data.

    Parameters
    ----------
    data : list[float]
        Input data points to analyze.
    threshold : float
        Minimum value to include in calculations.

    Returns
    -------
    dict[str, float]
        Dictionary containing 'mean', 'std', and 'count' metrics.
    """
```

### Use Google Python Style Naming Conventions

Naming conventions follow the 
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#3164-guidelines-derived-from-guidos-recommendations).

| Type                       | Public               | Internal                          |
| :------------------------- | :------------------- | :-------------------------------- |
| Packages                   | `lower_with_under`   |
| Modules                    | `lower_with_under`   | `_lower_with_under`               |
| Classes                    | `CapWords`           | `_CapWords`                       |
| Exceptions                 | `CapWords`           |
| Functions                  | `lower_with_under()` | `_lower_with_under()`             |
| Global/Class Constants     | `CAPS_WITH_UNDER`    | `_CAPS_WITH_UNDER`                |
| Global/Class Variables     | `lower_with_under`   | `_lower_with_under`               |
| Instance Variables         | `lower_with_under`   | `_lower_with_under` (protected)   |
| Method Names               | `lower_with_under()` | `_lower_with_under()` (protected) |
| Function/Method Parameters | `lower_with_under`   |
| Local Variables            | `lower_with_under`   |

### Define dot-accessible interfaces by re-exporting public objects via the package's \_\_init\_\_.py module

There are several examples in the repo of this pattern, but here is a simple one:
```
|-automobiles/
  |-automobiles/
    |-__init__.py  // re-exports Automobile and chassis
    |-_automobile.py  // defines class Automobile
    |-chassis/
      |-__init__.py
      |-_sedan.py
      |-_truck.py
  |-tests/
  |-README.md
```

```python
# automobiles/automobiles/__init__.py
from automobiles import chassis  # make chassis dot-accessible via automobiles.chassis
from automobiles._automobile import Automobile

__all__ = [
    "Automobile", 
    "chassis"
]
```

```python
# some_script.py
import automobiles

automobile = automobiles.Automobile(chassis=automobiles.chassis.Sedan)
```

## Git Naming Conventions

### Follow Git Naming Conventions

#### Branch Names
- Prefix branch names with the Jira ticket ID or `NOISSUE`
- Follow `kebab-case`
- The branch name briefly describes code changes on that branch.

**GOOD examples**
- `DI-123-demo-a-pull-request`
- `feature/DI-123-add-custom-baselining-pipeline`
- `NOISSUE-demo-a-pull-request`
- `DI-123-demo-a-pull-request-20260416`

**BAD examples**
- `some-changes-20260416` is missing an appropriate prefix
- `NOISSUE-some-changes` is too vague


#### Commit Messages

- Prefix the commit message with the Jira ticket ID or `NOISSUE:`
- Write in imperative mood
- Long-form commit messages are exceptional

**Good examples**

- `DI-16380 Sleep between retries`
- `DI-16380: Sleep between retries`
- `NOISSUE: Sleep between retries`
- 
    ```
    DI-16380 Sleep between retries

    The hypothesis is pytest doesn't complete teardown before exiting, 
    leading to port competition with the previous run. Port conflicts 
    began failing test runs after retries were introduced, 
    and the first test run never fails due to port conflicts.

    Furthermore, retries have improved build success rate, 
    so removing the retry loop is not a first-choice option.
    ```

**Bad examples**

- `tests are updated` is missing an appropriate prefix
- `NOISSUE: Update MyClass` is too vague
- `DI-16380 Retries are separated by sleeps` is in passive voice
