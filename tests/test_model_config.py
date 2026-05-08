"""Tests for model configuration service."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.services.model_config import (
    clear_model_config,
    load_model_config,
    save_model_config,
)


def test_load_empty_config():
    with patch('backend.services.model_config._get_config_file') as mock_file:
        mock_file.return_value = Path(tempfile.gettempdir()) / 'nonexistent_mediatools_test.json'
        config = load_model_config()
        assert config == {'baseUrl': '', 'model': '', 'apiKey': ''}


def test_save_and_load_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / 'config.json'
        with patch('backend.services.model_config._get_config_file') as mock_file:
            mock_file.return_value = config_file
            test_config = {
                'baseUrl': 'https://api.example.com',
                'model': 'gpt-4',
                'apiKey': 'sk-test123',
            }
            saved = save_model_config(test_config)
            assert saved == test_config
            assert config_file.exists()
            loaded = load_model_config()
            assert loaded == test_config


def test_save_config_trims_whitespace():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / 'config.json'
        with patch('backend.services.model_config._get_config_file') as mock_file:
            mock_file.return_value = config_file
            saved = save_model_config({
                'baseUrl': '  https://api.example.com  ',
                'model': '  gpt-4  ',
                'apiKey': '  sk-test123  ',
            })
            assert saved['baseUrl'] == 'https://api.example.com'
            assert saved['model'] == 'gpt-4'
            assert saved['apiKey'] == 'sk-test123'


def test_clear_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / 'config.json'
        with patch('backend.services.model_config._get_config_file') as mock_file:
            mock_file.return_value = config_file
            save_model_config({
                'baseUrl': 'https://api.example.com',
                'model': 'gpt-4',
                'apiKey': 'sk-test123',
            })
            assert config_file.exists()
            clear_model_config()
            assert not config_file.exists()
            loaded = load_model_config()
            assert loaded == {'baseUrl': '', 'model': '', 'apiKey': ''}
