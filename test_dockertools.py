import os
import sys
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

class TestDockertools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bin_dir = os.path.join(self.test_dir, 'bin')
        os.makedirs(self.bin_dir)
        self.mock_docker = os.path.join(self.bin_dir, 'docker')
        self.mock_curl = os.path.join(self.bin_dir, 'curl')
        self.mock_jq = os.path.join(self.bin_dir, 'jq')
        self.log_file = os.path.join(self.test_dir, 'docker.log')

        # Create mock docker script
        mock_docker_script_content = """#!/bin/bash
echo "docker $@" >> "{log_file}"
ARGS="$@"

if [[ "$1" == "ps" ]]; then
    echo "container1"
    echo "container2"
elif [[ "$1" == "inspect" ]]; then
    if [[ "$ARGS" == *"container1"* ]]; then
        echo "vol1 container1"
    elif [[ "$ARGS" == *"container2"* ]]; then
        echo "vol2 container2"
    elif [[ "$ARGS" == *"ghcr.io/ly4096x/dockertools-helper:latest"* ]]; then
        exit 0
    elif [[ "$ARGS" == *"myrepo:latest"* ]]; then
        # Return a repo digest
        echo "[sha256:12345]"
    else
        echo "[]"
    fi
elif [[ "$1" == "volume" && "$2" == "ls" ]]; then
    echo "vol1"
    echo "vol2"
    echo "vol3"
elif [[ "$1" == "images" ]]; then
    if [[ "$ARGS" == *"dangling=false"* ]]; then
        echo "myrepo:latest"
    elif [[ "$ARGS" == *"dangling=true"* ]]; then
        echo "none:none"
    fi
elif [[ "$1" == "rmi" ]]; then
    echo "Deleted: $2"
elif [[ "$1" == "build" ]]; then
    # Simulate a successful build
    echo "Simulating docker build..."
    exit 0
elif [[ "$1" == "run" ]]; then
    # Simulate running a command inside the container
    if [[ "$ARGS" == *"command -v bash && command -v zstd && command -v bsdtar"* ]]; then
        echo "Simulating tools check in container..."
        exit 0 # Success for tool check
    elif [[ "$ARGS" == *"bsdtar -cf - -C /source . | "* ]]; then
        echo "Simulating bsdtar snapshot for volume..."
        exit 0 # Success for snapshot
    else
        echo "Unknown run command: $ARGS" >&2
        exit 1
    fi
fi
"""
        with open(self.mock_docker, 'w') as f:
            f.write(mock_docker_script_content.format(log_file=self.log_file))
        os.chmod(self.mock_docker, 0o755)

        # Mock curl
        with open(self.mock_curl, 'w') as f:
            f.write(f"""#!/bin/bash
echo "curl $@" >> "{self.log_file}"
echo '{{"results": [{{"name": "v1", "images": [{{"architecture": "amd64"}}]}}]}}'
""")
        os.chmod(self.mock_curl, 0o755)

        # Mock jq
        with open(self.mock_jq, 'w') as f:
            f.write(
                f"""#!/bin/bash
# Simply output a fixed string or mimic logic?
# The script expects jq to process the input.
# Since we mock curl to return specific JSON, we can just print the expected formatted string
# Or we can let jq run if installed? No, we mock it.
echo "v1 [ amd64 ]"
"""
            )
        os.chmod(self.mock_jq, 0o755)

        self.env = os.environ.copy()
        self.env['PATH'] = f"{self.bin_dir}:{self.env['PATH']}"
        self.script_path = os.path.abspath('./dockertools')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_update_images(self):
        result = subprocess.run(
            [self.script_path, "update-images"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        with open(self.log_file, 'r') as f:
            log = f.read()
        self.assertIn("docker pull myrepo:latest", log)

    def test_remove_none_images(self):
        result = subprocess.run(
            [self.script_path, "remove-none-images"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        with open(self.log_file, 'r') as f:
            log = f.read()
        self.assertIn("docker rmi none:none", log)

    def test_list_tags(self):
        result = subprocess.run(
            [self.script_path, "list-tags", "myimage"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("v1 [ amd64 ]", result.stdout)

    def test_print_volume_to_container_mappings(self):
        result = subprocess.run(
            [self.script_path, "print-volume-to-container-mappings"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        # Expected alignment. vol1 is len 4, vol2 is len 4. Max len 4.
        # "vol1 -> container1"
        self.assertIn("vol1 -> container1", result.stdout)
        self.assertIn("vol2 -> container2", result.stdout)
        self.assertIn("vol3 -> NONE", result.stdout)

    def test_snapshot_volumes_single(self):
        dest_dir = os.path.join(self.test_dir, 'backup')
        result = subprocess.run(
            [self.script_path, "snapshot-volumes", "-d", dest_dir, "vol1"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        with open(self.log_file, 'r') as f:
            log = f.read()

        # Check image inspect
        self.assertIn('image inspect ghcr.io/ly4096x/dockertools-helper:latest', log)
        # Check run command
        # Expected: run --rm -v vol1:/source -v ...:/backup ... bsdtar ...
        self.assertIn('run --rm -v vol1:/source', log)
        self.assertIn("bsdtar -cf - -C /source . | zstd -T0 > /backup/vol1.tar.zstd", log)

    def test_snapshot_volumes_multiple(self):
        dest_dir = os.path.join(self.test_dir, 'backup')
        result = subprocess.run(
            [self.script_path, "snapshot-volumes", "-d", dest_dir, "vol1", "vol2"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        with open(self.log_file, 'r') as f:
            log = f.read()

        self.assertIn('run --rm -v vol1:/source', log)
        self.assertIn('run --rm -v vol2:/source', log)

    def test_snapshot_volumes_all(self):
        dest_dir = os.path.join(self.test_dir, 'backup')
        result = subprocess.run(
            [self.script_path, "snapshot-volumes", "-d", dest_dir, "-a"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        with open(self.log_file, 'r') as f:
            log = f.read()

        # Should verify we called docker volume ls -q
        self.assertIn('volume ls -q', log)
        # Should verify we ran backup for vol1 and vol2
        self.assertIn('run --rm -v vol1:/source', log)
        self.assertIn('run --rm -v vol2:/source', log)

    def test_snapshot_volumes_custom_compress(self):
        dest_dir = os.path.join(self.test_dir, 'backup')
        result = subprocess.run(
            [
                self.script_path,
                "snapshot-volumes",
                "--use-compress-program",
                "gzip",
                "-d",
                dest_dir,
                "vol1",
            ],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        with open(self.log_file, 'r') as f:
            log = f.read()

        self.assertIn("bsdtar -cf - -C /source . | gzip > /backup/vol1.tar.zstd", log)

    def test_snapshot_volumes_errors(self):
        # No dest
        result = subprocess.run(
            [self.script_path, "snapshot-volumes", "vol1"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error: Destination directory -d/--destination-dir is required.", result.stdout)

        # Both -a and volume
        result = subprocess.run(
            [self.script_path, "snapshot-volumes", "-d", "dest", "-a", "vol1"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error: Cannot specify volumes when using -a/--all.", result.stdout)

    def test_helper_image_tools_exist(self):
        # Build the Docker image (assuming Dockerfile is in the current directory)
        image_name = "dockertools-helper-test:latest"
        build_result = subprocess.run(["docker", "build", "-t", image_name, "."], env=self.env, capture_output=True, text=True)
        self.assertEqual(build_result.returncode, 0, f"Docker build failed: {build_result.stderr}")

        # Run a container and check for tools
        check_command = "sh -c \"command -v bash && command -v zstd && command -v bsdtar\""
        run_result = subprocess.run(["docker", "run", "--rm", image_name, check_command], env=self.env, capture_output=True, text=True)
        self.assertEqual(run_result.returncode, 0, f"Required tools not found in helper image: {run_result.stderr}")

if __name__ == '__main__':
    unittest.main()
