import unittest
import subprocess
import os
import shutil
import sys

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build the image with the tag used by the script
        print("Building helper image...")
        subprocess.check_call(["docker", "build", "-t", "ghcr.io/ly4096x/dockertools-helper:latest", "."])
        
    def setUp(self):
        self.script_path = os.path.abspath("./dockertools")
        self.backup_dir = os.path.abspath("./backup_test")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.volume_name = "integration_test_vol"
        
        # Create volume and populate
        subprocess.check_call(["docker", "volume", "create", self.volume_name])
        # Use a small alpine container to write a file
        subprocess.check_call([
            "docker", "run", "--rm", "-v", f"{self.volume_name}:/data", "alpine",
            "sh", "-c", "echo 'hello world' > /data/test.txt"
        ])

    def tearDown(self):
        shutil.rmtree(self.backup_dir, ignore_errors=True)
        subprocess.call(["docker", "volume", "rm", self.volume_name])

    def test_snapshot_volume(self):
        print(f"Testing snapshot of volume: {self.volume_name}")
        
        # Run the snapshot command
        # The script uses 'ghcr.io/ly4096x/dockertools-helper:latest' by default.
        # Since we built it locally, it should find it and use it.
        
        cmd = [self.script_path, "snapshot-volumes", "-d", self.backup_dir, self.volume_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
        self.assertEqual(result.returncode, 0, "dockertools snapshot-volumes failed")
        
        expected_file = os.path.join(self.backup_dir, f"{self.volume_name}.tar.zstd")
        self.assertTrue(os.path.exists(expected_file), f"Backup file {expected_file} not created")
        
        # Verify content using the helper image itself (ensures bsdtar/zstd are working in the image)
        verify_cmd = [
            "docker", "run", "--rm", 
            "-v", f"{self.backup_dir}:/backup",
            "ghcr.io/ly4096x/dockertools-helper:latest",
            "bsdtar", "-tf", f"/backup/{self.volume_name}.tar.zstd", "--use-compress-program", "zstd"
        ]
        
        print("Verifying backup content...")
        verify_res = subprocess.run(verify_cmd, capture_output=True, text=True)
        
        if verify_res.returncode != 0:
            print("Verify STDOUT:", verify_res.stdout)
            print("Verify STDERR:", verify_res.stderr)
            
        self.assertEqual(verify_res.returncode, 0, "Failed to list archive content")
        self.assertIn("test.txt", verify_res.stdout, "test.txt not found in archive")

if __name__ == '__main__':
    unittest.main()
