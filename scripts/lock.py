""" environment locking for jupyter[lab]-lsp
"""
import os
from pathlib import Path
import json
from ruamel_yaml import safe_load, safe_dump
import tempfile
import subprocess
import platform
from doit.tools import config_changed


DOIT_CONFIG = {
    "backend": "sqlite3",
    "verbosity": 2,
    "par_type": "thread",
    "default_tasks": ["lock"]
}

WIN = platform.system() == "Windows"
OSX = platform.system() == "Darwin"
LINUX = platform.system() == "Linux"

ROOT = Path(__file__).parent.parent.resolve()

GITHUB = ROOT / ".github"
WORKFLOWS = GITHUB / "workflows"
LOCKS = GITHUB / "conda.locks"

WORKFLOW_LINT = WORKFLOWS / "job.lint.yml"
WORKFLOW_TEST = WORKFLOWS / "job.test.yml"

WORKFLOW_LINT_YML = safe_load(WORKFLOW_LINT.read_text())
WORKFLOW_TEST_YML = safe_load(WORKFLOW_TEST.read_text())

TEST_MATRIX = WORKFLOW_TEST_YML["jobs"]["acceptance"]["strategy"]["matrix"]
LINT_MATRIX = WORKFLOW_LINT_YML["jobs"]["lint"]["strategy"]["matrix"]

REQS = ROOT / "requirements"

class ENV:
    atest = REQS / "atest.yml"
    ci = REQS / "ci.yml"
    lint = REQS / "lint.yml"
    utest = REQS / "utest.yml"
    win = REQS / "win.yml"

CHN = "channels"
DEP = "dependencies"


def _make_lock_task(kind_, env_files, extra_deps, config, platform_, python_, nodejs_, lab_):
    """ generate a single dodo excursion for conda-lock
    """
    if platform_ == "win-64":
        env_files = [*env_files, ENV.win]

    lockfile = LOCKS / f"conda.{kind_}.{platform_}-{python_}-{lab_}.lock"
    file_dep = [*env_files, *extra_deps]

    def expand_specs(specs):
        from conda.models.match_spec import MatchSpec

        for raw in specs:
            match = MatchSpec(raw)
            yield match.name, [raw, match]

    def merge(composite, env):
        for channel in reversed(env.get(CHN, [])):
            if channel not in composite.get(CHN, []):
                composite[CHN] = [channel, *composite.get(CHN, [])]

        comp_specs = dict(expand_specs(composite.get(DEP, [])))
        env_specs = dict(expand_specs(env.get(DEP, [])))

        composite[DEP] = sorted([
            raw for (raw, match) in env_specs.values()
        ] + [
            raw for name, (raw, match) in comp_specs.items() if name not in env_specs
        ])

        return composite


    def _lock():
        composite = dict()

        for env_dep in env_files:
            print(f"merging {env_dep.name}", flush=True)
            composite = merge(composite, safe_load(env_dep.read_text()))

        fake_env = {
            DEP: [
                f"python ={python_}.*",
                f"jupyterlab ={lab_}.*",
                f"nodejs ={nodejs_}.*",
            ]
        }
        composite = merge(composite, fake_env)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            composite_yml = tdp / "composite.yml"
            composite_yml.write_text(safe_dump(composite, default_flow_style=False))
            print("composite\n\n", composite_yml.read_text(), "\n\n", flush=True)
            rc = 1
            for extra_args in [[], ["--no-mamba"]]:
                args = [
                    "conda-lock", "-p", platform_,
                    "-f", str(composite_yml)
                ] + extra_args
                print(">>>", " ".join(args), flush=True)
                rc = subprocess.call(args, cwd=str(tdp))
                if rc == 0:
                    break

            if rc != 0:
                raise Exception("couldn't solve at all", composite)

            tmp_lock = tdp / f"conda-{platform_}.lock"
            tmp_lock_txt = tmp_lock.read_text()
            tmp_lock_lines = tmp_lock_txt.splitlines()
            urls = [line for line in tmp_lock_lines if line.startswith("https://")]
            print(len(urls), "urls")
            if not lockfile.parent.exists():
                lockfile.parent.mkdir()
            lockfile.write_text(tmp_lock_txt)

    return dict(
        name=lockfile.name,
        uptodate=[config_changed(config)],
        file_dep=file_dep,
        actions=[_lock],
        targets=[lockfile]
    )


def _iter_lock_args(matrix):
    for platform_ in matrix["platform"]:
        for python_ in matrix["python"]:
            for lab_ in matrix["lab"]:
                nodejs_ = None

                for include in matrix["include"]:
                    if "nodejs" not in include:
                        continue
                    if include['python'] == python_:
                        nodejs_ = include['nodejs']
                        break

                assert nodejs_ is not None
                yield platform_, python_, nodejs_, lab_

# Not part of normal business

def task_lock():
    """lock conda envs so they don't need to be solved in CI
    This should be run semi-frequently (e.g. after merge to master).
    Requires `conda-lock` CLI to be available
    """

    for task_args in _iter_lock_args(TEST_MATRIX):
        yield _make_lock_task(
            "test",
            [ENV.ci, ENV.utest, ENV.atest],
            [WORKFLOW_TEST],
            TEST_MATRIX,
            *task_args
        )

    for task_args in _iter_lock_args(LINT_MATRIX):
        yield _make_lock_task(
            "lint",
            [ENV.ci, ENV.lint],
            [WORKFLOW_LINT],
            LINT_MATRIX,
            *task_args
        )


if __name__ == '__main__':
    import doit
    doit.run(globals())