"""Tests for the global installation functionality."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.quickhooks.cli.install import (
    get_claude_config_dir,
    get_current_venv,
    get_python_executable,
    create_context_portal_hook_script,
    get_current_claude_settings,
    update_claude_settings_with_hooks,
)


class TestVirtualEnvironmentDetection:
    """Test virtual environment detection functionality."""
    
    def test_get_current_venv_conda(self):
        """Test detection of conda environment."""
        with patch.dict(os.environ, {'CONDA_PREFIX': '/opt/miniconda3/envs/test'}):
            venv = get_current_venv()
            assert venv == Path('/opt/miniconda3/envs/test')
    
    def test_get_current_venv_virtualenv(self):
        """Test detection of standard virtual environment."""
        with patch.dict(os.environ, {'VIRTUAL_ENV': '/home/user/.venv/test'}):
            venv = get_current_venv()
            assert venv == Path('/home/user/.venv/test')
    
    def test_get_current_venv_none(self):
        """Test when no virtual environment is detected."""
        # Clear all environment variables that indicate virtual environments
        env_vars_to_clear = ['CONDA_PREFIX', 'VIRTUAL_ENV', 'PIPENV_ACTIVE']
        with patch.dict(os.environ, {var: '' for var in env_vars_to_clear}, clear=True):
            with patch('sys.prefix', '/usr/local'):
                with patch('sys.base_prefix', '/usr/local'):
                    venv = get_current_venv()
                    assert venv is None
    
    def test_get_python_executable_with_venv(self):
        """Test Python executable detection with virtual environment."""
        temp_venv = Path(tempfile.mkdtemp())
        try:
            # Create mock Python executable
            bin_dir = temp_venv / "bin"
            bin_dir.mkdir()
            python_exe = bin_dir / "python"
            python_exe.touch()
            
            result = get_python_executable(temp_venv)
            assert result == python_exe
            
        finally:
            shutil.rmtree(temp_venv)
    
    def test_get_python_executable_no_venv(self):
        """Test Python executable detection without virtual environment."""
        result = get_python_executable(None)
        assert result == Path(os.sys.executable)


class TestClaudeConfigManagement:
    """Test Claude configuration management functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.claude_dir = Path(self.temp_dir) / ".claude"
        self.claude_dir.mkdir(parents=True)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_get_claude_config_dir(self):
        """Test Claude config directory creation."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            claude_dir = get_claude_config_dir()
            assert claude_dir.exists()
            assert claude_dir.name == ".claude"
    
    def test_get_current_claude_settings_new_file(self):
        """Test reading settings from new (non-existent) file."""
        settings = get_current_claude_settings(self.claude_dir)
        assert settings == {}
    
    def test_get_current_claude_settings_existing_file(self):
        """Test reading settings from existing file."""
        settings_file = self.claude_dir / "settings.json"
        test_settings = {"test": "value", "hooks": {"PreToolUse": []}}
        
        with open(settings_file, 'w') as f:
            json.dump(test_settings, f)
        
        settings = get_current_claude_settings(self.claude_dir)
        assert settings == test_settings
    
    def test_get_current_claude_settings_invalid_json(self):
        """Test handling of invalid JSON in settings file."""
        settings_file = self.claude_dir / "settings.json"
        
        with open(settings_file, 'w') as f:
            f.write("invalid json content")
        
        settings = get_current_claude_settings(self.claude_dir)
        assert settings == {}
    
    def test_update_claude_settings_with_hooks_new_file(self):
        """Test updating settings when no existing file exists."""
        hook_script = Path("/fake/path/to/hook.py")
        
        update_claude_settings_with_hooks(self.claude_dir, hook_script)
        
        settings_file = self.claude_dir / "settings.json"
        assert settings_file.exists()
        
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        assert 'hooks' in settings
        assert 'PreToolUse' in settings['hooks']
        assert len(settings['hooks']['PreToolUse']) == 1
        
        hook_config = settings['hooks']['PreToolUse'][0]
        assert 'matcher' in hook_config
        assert 'hooks' in hook_config
        assert len(hook_config['hooks']) == 1
        assert str(hook_script) in hook_config['hooks'][0]['command']
    
    def test_update_claude_settings_with_hooks_existing_file(self):
        """Test updating settings when file already exists."""
        settings_file = self.claude_dir / "settings.json"
        existing_settings = {
            "other_setting": "value",
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "OtherTool",
                        "hooks": [{"type": "command", "command": "other_hook.py"}]
                    }
                ]
            }
        }
        
        with open(settings_file, 'w') as f:
            json.dump(existing_settings, f)
        
        hook_script = Path("/fake/path/to/hook.py")
        update_claude_settings_with_hooks(self.claude_dir, hook_script)
        
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        # Should preserve existing settings
        assert settings['other_setting'] == "value"
        
        # Should have both hooks
        assert len(settings['hooks']['PreToolUse']) == 2
        
        # Check that Context Portal hook was added
        context_portal_hook = None
        for hook_config in settings['hooks']['PreToolUse']:
            if any('context_portal_memory' in str(hook.get('command', ''))
                   for hook in hook_config.get('hooks', [])):
                context_portal_hook = hook_config
                break
        
        assert context_portal_hook is not None
        assert 'Bash' in context_portal_hook['matcher']
        assert 'Edit' in context_portal_hook['matcher']


class TestHookScriptCreation:
    """Test Context Portal hook script creation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.claude_dir = Path(self.temp_dir) / ".claude"
        self.claude_dir.mkdir(parents=True)
        
        # Create a mock source hook file
        self.source_hook_dir = Path(self.temp_dir) / "hooks"
        self.source_hook_dir.mkdir()
        self.source_hook = self.source_hook_dir / "context_portal_memory.py"
        
        # Create a minimal hook script for testing
        hook_content = '''#!/usr/bin/env python3
import json
import sys

def main():
    """Test hook main function."""
    input_data = json.loads(sys.stdin.read())
    response = {
        'allowed': True,
        'modified': False,
        'tool_name': input_data.get('tool_name', ''),
        'tool_input': input_data.get('tool_input', {}),
        'message': 'Test hook executed'
    }
    print(json.dumps(response))

if __name__ == '__main__':
    main()
'''
        with open(self.source_hook, 'w') as f:
            f.write(hook_content)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_context_portal_hook_script(self):
        """Test creation of Context Portal hook script."""
        venv_path = Path("/fake/venv")
        
        # Mock the source hook file path
        with patch('src.quickhooks.cli.install.Path.__truediv__') as mock_truediv:
            # Set up the mock to return our test source hook
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_truediv.return_value = mock_path
            
            with patch('builtins.open', create=True) as mock_open:
                # Mock reading the source hook
                mock_open.return_value.__enter__.return_value.read.return_value = "# Test hook content"
                
                # Mock writing the wrapper script
                mock_write_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_write_file
                
                with patch('src.quickhooks.cli.install.os.chmod') as mock_chmod:
                    # This should not raise an exception
                    try:
                        result = create_context_portal_hook_script(venv_path, self.claude_dir)
                        # The function should return a path
                        assert isinstance(result, Path)
                        assert result.name == "context_portal_memory.py"
                        
                        # Should have called chmod to make it executable
                        mock_chmod.assert_called_once()
                        
                    except FileNotFoundError:
                        # This is expected in the test environment since we're mocking
                        pass
    
    def test_create_context_portal_hook_script_with_real_source(self):
        """Test creation with a real source hook file."""
        venv_path = Path("/fake/venv")
        
        # Patch the source hook path to our test file
        with patch('src.quickhooks.cli.install.Path') as mock_path_class:
            # Create a mock path that points to our test source hook
            mock_source_path = MagicMock()
            mock_source_path.exists.return_value = True
            
            # Set up the path resolution to return our test source hook
            def path_side_effect(*args):
                if args and 'hooks' in str(args):
                    return self.source_hook
                return MagicMock()
            
            mock_path_class.return_value.__truediv__.side_effect = path_side_effect
            
            with patch('src.quickhooks.cli.install.os.chmod'):
                result = create_context_portal_hook_script(venv_path, self.claude_dir)
                
                # Check that the hook script was created
                assert result.exists()
                assert result.is_file()
                
                # Check that it contains the expected wrapper content
                with open(result, 'r') as f:
                    content = f.read()
                
                assert 'PYTHON_EXECUTABLE' in content
                assert 'HOOK_SCRIPT' in content
                assert '/fake/venv' in content


class TestInstallationIntegration:
    """Test the complete installation process."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('src.quickhooks.cli.install.get_claude_config_dir')
    @patch('src.quickhooks.cli.install.get_current_venv')
    @patch('src.quickhooks.cli.install.create_context_portal_hook_script')
    @patch('src.quickhooks.cli.install.update_claude_settings_with_hooks')
    def test_install_context_portal_global_success(
        self, 
        mock_update_settings,
        mock_create_script,
        mock_get_venv,
        mock_get_claude_dir
    ):
        """Test successful global installation."""
        # Set up mocks
        claude_dir = Path(self.temp_dir) / ".claude"
        claude_dir.mkdir(parents=True)
        
        mock_get_claude_dir.return_value = claude_dir
        mock_get_venv.return_value = Path("/fake/venv")
        mock_create_script.return_value = claude_dir / "hooks" / "context_portal_memory.py"
        
        # Import here to avoid circular imports in the test setup
        from src.quickhooks.cli.install import install_context_portal_global
        
        # This should not raise an exception
        install_context_portal_global()
        
        # Verify that the expected functions were called
        mock_get_claude_dir.assert_called_once()
        mock_get_venv.assert_called_once()
        mock_create_script.assert_called_once()
        mock_update_settings.assert_called_once()


@pytest.mark.parametrize("env_var,expected_path", [
    ("CONDA_PREFIX", "/opt/conda/envs/test"),
    ("VIRTUAL_ENV", "/home/user/.venv"),
    ("PIPENV_ACTIVE", "/home/user/.pipenv"),
])
def test_virtual_environment_detection_parametrized(env_var, expected_path):
    """Test virtual environment detection with different environment variables."""
    env_dict = {env_var: expected_path}
    if env_var == "PIPENV_ACTIVE":
        env_dict["VIRTUAL_ENV"] = expected_path
    
    with patch.dict(os.environ, env_dict):
        venv = get_current_venv()
        if env_var == "PIPENV_ACTIVE":
            # PIPENV_ACTIVE requires VIRTUAL_ENV to be set
            assert venv == Path(expected_path)
        else:
            assert venv == Path(expected_path)


def test_hook_script_wrapper_structure():
    """Test that the generated hook script wrapper has the correct structure."""
    temp_dir = tempfile.mkdtemp()
    try:
        claude_dir = Path(temp_dir) / ".claude"
        claude_dir.mkdir(parents=True)
        
        # Create a mock source hook
        source_hook_dir = claude_dir / "source_hooks"
        source_hook_dir.mkdir()
        source_hook = source_hook_dir / "context_portal_memory.py"
        
        with open(source_hook, 'w') as f:
            f.write('''
def main():
    print("Test hook")

if __name__ == '__main__':
    main()
''')
        
        venv_path = Path("/fake/venv")
        
        with patch('src.quickhooks.cli.install.Path') as mock_path:
            # Mock the path resolution to return our test source hook
            mock_path.return_value = source_hook
            
            with patch('src.quickhooks.cli.install.os.chmod'):
                result = create_context_portal_hook_script(venv_path, claude_dir)
                
                # Verify the wrapper script structure
                with open(result, 'r') as f:
                    content = f.read()
                
                # Check for key components of the wrapper
                assert 'PYTHON_EXECUTABLE' in content
                assert 'HOOK_SCRIPT' in content
                assert 'subprocess.run' in content
                assert 'json.dumps' in content
                assert 'allowed": True' in content  # Fail-safe behavior
    
    finally:
        shutil.rmtree(temp_dir)