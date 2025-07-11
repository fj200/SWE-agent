import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from datasets import load_dataset
from pydantic import BaseModel, ConfigDict, Field
from swerex.deployment.config import (
    DeploymentConfig,
    DockerDeploymentConfig,
    DummyDeploymentConfig,
    LocalDeploymentConfig,
)

from sweagent.agent.problem_statement import (
    SWEBenchMultimodalProblemStatement,
    TextProblemStatement,
)
from sweagent.environment.repo import GithubRepoConfig, LocalRepoConfig, PreExistingRepoConfig
from sweagent.environment.swe_env import EnvironmentConfig
from sweagent.utils.files import load_file
from sweagent.utils.log import get_logger

logger = get_logger("swea-config", emoji="🔧")


class InstancesConfig(BaseModel):
    type: str = "file"
    path: str | None = None
    deployment: DockerDeploymentConfig | None = Field(
        default_factory=lambda: DockerDeploymentConfig(image="python:3.11"),
        description="Deployment configuration for instances.",
    )
    # Allow arbitrary extra fields for CLI parsing
    model_config = ConfigDict(extra="allow")


class BatchInstance:
    """A single instance in a batch of instances."""

    def __init__(self, env: EnvironmentConfig, problem_statement: Any):
        self.env = env
        self.problem_statement = problem_statement


class InstanceSource:
    """
    Unified loader for batch instances from various sources.
    Register new sources by adding loader functions to the LOADERS dict.
    """

    LOADERS: dict[str, Callable[[dict, DeploymentConfig | None], list[BatchInstance]]] = {}

    def __init__(self, config: Any):
        self.source_type = config.instances.type
        self.source_config = config.instances.model_dump()
        # Handle deployment configuration
        if config.instances.deployment is not None:
            self.deployment = config.instances.deployment
        else:
            self.deployment = DockerDeploymentConfig(image="python:3.11")

    @classmethod
    def register_loader(cls, name: str):
        def decorator(fn):
            cls.LOADERS[name] = fn
            return fn

        return decorator

    def get_instances(self) -> list[BatchInstance]:
        loader = self.LOADERS[self.source_type]
        return loader(self.source_config, self.deployment)


# --- Loader Implementations ---


def _to_batch_instance(instance: dict, deployment: DeploymentConfig = None) -> BatchInstance:
    """Convert a simple instance dict to a BatchInstance."""

    instance_id = instance.get("instance_id", instance.get("id"))

    extra_fields = instance.get("extra_fields", {})
    if "issue_images" in extra_fields:
        problem_statement = SWEBenchMultimodalProblemStatement(
            text=instance["problem_statement"],
            issue_images=extra_fields.pop("issue_images"),
            id=instance_id,
            extra_fields=extra_fields,
        )
    else:
        problem_statement = TextProblemStatement(
            text=instance["problem_statement"],
            id=instance_id,
            extra_fields=extra_fields,
        )

    # Repo config
    repo_name = instance.get("repo_name", instance.get("repo", ""))
    base_commit = instance.get("base_commit", "HEAD")
    if not repo_name:
        repo = None
    elif "github" in repo_name:
        repo = GithubRepoConfig(github_url=repo_name, base_commit=base_commit)
    elif "/" not in repo_name:
        repo = PreExistingRepoConfig(repo_name=repo_name, base_commit=base_commit)
    else:
        repo = LocalRepoConfig(path=Path(repo_name), base_commit=base_commit)

    # Deployment
    if isinstance(deployment, LocalDeploymentConfig):
        if instance.get("image_name", False):
            msg = "Local deployment does not support image_name"
            raise ValueError(msg)
        return BatchInstance(
            env=EnvironmentConfig(deployment=deployment, repo=repo), problem_statement=problem_statement
        )
    if isinstance(deployment, DummyDeploymentConfig):
        return BatchInstance(
            env=EnvironmentConfig(deployment=deployment, repo=repo), problem_statement=problem_statement
        )

    # Handle Docker deployment with image_name from instance
    if isinstance(deployment, DockerDeploymentConfig):
        if instance.get("image_name"):
            deployment.image = instance["image_name"]
        if deployment.python_standalone_dir is None:
            # Note: you can disable this by setting python_standalone_dir to ""
            deployment.python_standalone_dir = "/root"  # type: ignore

    env = EnvironmentConfig(deployment=deployment, repo=repo)

    return BatchInstance(env=env, problem_statement=problem_statement)


@InstanceSource.register_loader("file")
def load_from_file(config: dict, deployment: DeploymentConfig | None) -> list[BatchInstance]:
    instance_dicts = load_file(Path(config["path"]))
    return [_to_batch_instance(inst, deployment) for inst in instance_dicts]


@InstanceSource.register_loader("swebench")
def load_from_swe_bench(config: dict, deployment: DeploymentConfig | None) -> list[BatchInstance]:
    def swe_bench_to_simple(inst: dict) -> dict:
        iid = inst["instance_id"]
        image_name = inst.get("image_name") or f"swebench/sweb.eval.x86_64.{iid.replace('__', '_1776_')}:latest".lower()
        extra_fields = inst.get("extra_fields", {})
        if "image_assets" in inst:
            issue_images = json.loads(inst["image_assets"]).get("problem_statement", [])
            extra_fields["issue_images"] = issue_images
        return {
            "image_name": image_name,
            "problem_statement": inst["problem_statement"],
            "instance_id": iid,
            "repo_name": inst.get("repo_name", "testbed"),
            "base_commit": inst.get("base_commit", "HEAD"),
            "extra_fields": extra_fields,
        }

    path = config["path"]
    try:
        instance_dicts = load_file(Path(path))
        instances = [swe_bench_to_simple(inst) for inst in instance_dicts]
    except FileNotFoundError as e:
        try:
            split = config.get("split", "dev")
            ds = load_dataset(path, split=split)
            instances = [swe_bench_to_simple(dict(inst)) for inst in ds]
        except:
            raise e

    if isinstance(deployment, DockerDeploymentConfig):
        deployment.platform = "linux/amd64"
    return [_to_batch_instance(inst, deployment) for inst in instances]


@InstanceSource.register_loader("swesmith")
def load_from_swe_smith(config: dict, deployment: DeploymentConfig | None) -> list[BatchInstance]:
    def convert_instance_dict(instance_dict: dict) -> dict:
        instance_dict["id"] = instance_dict["instance_id"]
        instance_dict["base_commit"] = instance_dict["id"]
        instance_dict["problem_statement"] = instance_dict.get("problem_statement", "")
        instance_dict["repo_name"] = "testbed"
        instance_dict["extra_fields"] = {"fail_to_pass": instance_dict["FAIL_TO_PASS"]}
        return instance_dict

    path = config["path"]
    try:
        instance_dicts = load_file(Path(path))
        instances = [convert_instance_dict(dict(inst)) for inst in instance_dicts]
    except FileNotFoundError as e:
        try:
            split = config.get("split", "train")
            instance_dicts = load_dataset(path, split)
            instances = [convert_instance_dict(dict(inst)) for inst in instance_dicts]
        except:
            raise e

    return [_to_batch_instance(inst, deployment) for inst in instances]
