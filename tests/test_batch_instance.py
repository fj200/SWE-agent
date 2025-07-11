import json

import pytest
from swerex.deployment.config import DockerDeploymentConfig

from sweagent.agent.problem_statement import TextProblemStatement
from sweagent.environment.repo import PreExistingRepoConfig
from sweagent.run.batch_instances import BatchInstance, InstanceSource


def test_swe_bench_instance_loading(test_data_sources_path):
    sb_instance = json.loads((test_data_sources_path / "swe-bench-dev-easy.json").read_text())[0]
    # Simulate loading a single instance via InstanceSource
    source = InstanceSource(
        source_type="swebench",
        source_config={"path": str(test_data_sources_path / "swe-bench-dev-easy.json")},
        deployment=DockerDeploymentConfig(image="python:3.11"),
    )
    instances = source.get_instances()
    instance = instances[0]
    assert isinstance(instance.env.repo, PreExistingRepoConfig)
    assert instance.env.repo.repo_name == "testbed"
    assert isinstance(instance.env.deployment, DockerDeploymentConfig)
    assert instance.env.deployment.image == "swebench/sweb.eval.x86_64.pydicom_1776_pydicom-1458:latest"
    assert isinstance(instance.problem_statement, TextProblemStatement)
    assert instance.problem_statement.text == sb_instance["problem_statement"]
    assert instance.problem_statement.id == "pydicom__pydicom-1458"


@pytest.mark.slow
def test_get_swe_bench_instances():
    for path, split in {
        ("SWE-bench/SWE-bench_Lite", "dev"),
        ("SWE-bench/SWE-bench_Lite", "test"),
        ("SWE-bench/SWE-bench_Verified", "test"),
        ("SWE-bench/SWE-bench_Multilingual", "test"),
        ("SWE-bench/SWE-bench", "dev"),
        ("SWE-bench/SWE-bench", "test"),
    }:
        print(path, split)
        source = InstanceSource(
            source_type="swebench",
            source_config={"path": path, "split": split},
            deployment=DockerDeploymentConfig(image="python:3.11"),
        )
        instances = source.get_instances()
        assert len(instances) > 0
        assert all(isinstance(instance, BatchInstance) for instance in instances)
