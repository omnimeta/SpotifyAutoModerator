import os
import sys
import logging
import yaml
from importlib import import_module
from inputimeout import inputimeout, TimeoutOccurred
import spotipy
from src.config_validator import ConfigValidator
from src.spotify_helper import SpotifyHelper
from src.integrity_manager import IntegrityManager
from src.playlist_cleaner import PlaylistCleaner


def main():

    if '-h' in sys.argv or '--help' in sys.argv:
        print_help_information()
        exit_with_code(0)
    elif '--rdc' in sys.argv:
        exit_with_code(restore_default_config_file())

    # An erroneous configuration may result in some playlist data loss
    # All configuration-file related issues must be therefore be resolved before proceeding
    try:
        (playlist_config, log_config, account_config) = load_configurations(path=get_config_filepath())
    except Exception as err:
        print('Error: \'%s\'' % err)
        print('Invalid configuration file')
        exit_with_code(1)

    config_validator = ConfigValidator(playlist_config, log_config, account_config)
    if not config_validator.is_valid():
        print('Invalid configuration file')
        exit_with_code(1)

    try:
        logger = setup_logger(log_config)
    except Exception as err:
        print('Error: \'$s\'' % err)
        exit_with_code(1)

    logger.info('Starting new session of SpotifyAutoModerator')
    try:
        api_client = SpotifyHelper(logger).configure_api(
            account_config['CLIENT_ID'],
            account_config['CLIENT_SECRET'],
            account_config['REDIRECT_URI']
        )
        if not isinstance(api_client, spotipy.client.Spotify):
            raise Exception('Failed to authenticate with Spotify')
    except Exception as err:
        logger.error('Error: \'%s\'', err)
        logger.error('Confirm your Spotify client/account details are correct in `data/config.yaml`')
        exit_with_code(1)

    if not config_validator.all_protected_playlists_exist(api_client):
        logger.error('Invalid configuration file')
        exit_with_code(1)

    moderate_playlists(logger, api_client, account_config['USERNAME'], playlist_config)
    sys.exit(0)


def moderate_playlists(logger, api_client, username, playlist_config):
    playlist_cleaner = PlaylistCleaner(logger, api_client, username, playlist_config)
    integrity_manager = IntegrityManager(logger, api_client, playlist_config)
    sp_helper = SpotifyHelper(logger)

    def protect_playlists():
        # runs one iteration of playlist moderation
        if playlist_config['PROTECT_ALL']:
            protected_playlists = sp_helper.get_all_collab_playlists(username, api=api_client)
        else:
            protected_playlists = []
            for playlist in playlist_config['PROTECTED_PLAYLISTS']:
                if len(playlist.keys()) == 1:
                    for key, val in playlist.items():
                        protected_playlists.append(val)

        for playlist in protected_playlists:
            print('') # newlines between playlists improves readibility of logs
            playlist_cleaner.run(playlist)
            integrity_manager.run(playlist)

    if '--loop' in sys.argv or '-l' in sys.argv:
        # For termination of loop mode, the idea is: delays between loop iterations are implemented
        # by a timeboxed attempt to  get user input (from stdin) in order to allow the user to
        # terminate the program loop without needing to send a kill signal
        while True:
            protect_playlists()
            logger.info('Completed iteration')
            if user_wants_to_exit(playlist_config['DELAY_BETWEEN_SCANS']):
                break
    else:
        protect_playlists()


def setup_logger(config):
    if not isinstance(config, dict):
        raise Exception('No log configuration was provided')
    for field in ['FILE_LEVEL', 'CONSOLE_LEVEL', 'FILE']:
        if (field not in config.keys()
            or not isinstance(config[field], str)
            or config[field] == ''):
            raise Exception('The provided log configuration does not include \'%s\'' % field)

    file_log_level = getattr(logging, config['FILE_LEVEL'].upper())
    console_log_level = getattr(logging, config['CONSOLE_LEVEL'].upper())

    file_handler = logging.FileHandler(config['FILE'])
    file_handler.setLevel(file_log_level)
    file_handler.set_name('file_handler')
    file_format = logging.Formatter(
        config['FILE_FORMAT'] if 'FILE_FORMAT' in config.keys()
        else '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.set_name('console_handler')
    console_handler.setLevel(console_log_level)
    console_format = logging.Formatter(
        config['CONSOLE_FORMAT'] if 'CONSOLE_FORMAT' in config.keys()
        else '%(name)s [%(levelname)s] - %(message)s')
    console_handler.setFormatter(console_format)

    logger = logging.getLogger('spautomod')
    logger.setLevel(min(file_handler.level, console_handler.level))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def user_wants_to_exit(timeout_after_secs):
    try:
        input = inputimeout(prompt='\nDo you want to quit? (Y/n): ', timeout=timeout_after_secs)
        if input in ['Y', 'y', 'YES', 'Yes', 'yes']:
            return True
    except TimeoutOccurred:
        return False
    return False


def load_configurations(path='data/config.yaml'):
    # finally block is used to ensure config file is closed
    # except block propagates error to upwards
    config_file = None
    try:
        config_file = open(path, 'r')
        config_data = yaml.load(config_file, Loader=yaml.FullLoader)
        return (
            config_data['PLAYLIST_CONFIG'],
            config_data['LOG_CONFIG'],
            config_data['ACCOUNT_CONFIG']
        )
    except yaml.YAMLError as err:
        raise err
    except Exception as err:
        raise err
    finally:
        if config_file is not None:
            config_file.close()


def restore_default_config_file():
    config_path = get_config_filepath()
    default_config_path = 'data/.default_config.yaml'
    default_config_file = None
    config_file = None

    print('Restoring the default configuration file will overwrite \'data/config.yaml\'')
    try:
        input = inputimeout(prompt='Are you sure you want to restore? (Y/n): ', timeout=30)
        if input not in ['Y', 'y', 'YES', 'Yes', 'yes']:
            print('Aborting restoration')
            return 0

        default_config_file = open(default_config_path, 'r')
        default_config_info = default_config_file.read()
        config_file = open(config_path, 'w')
        config_file.write(default_config_info)
    except TimeoutOccurred:
        print('Timed out. Aborting restoration')
        return 1
    except Exception as err:
        print('Error: \'%s\'' % err )
        print('Aborting restoration')
        return 1
    else:
        print('Restored default configuration file')
    finally:
        if default_config_file is not None:
            default_config_file.close()
        if config_file is not None:
            config_file.close()
    return 0


def get_config_filepath():
    # This function allows other paths to be more conveniently used during testing
    return 'data/config.yaml'


def exit_with_code(exit_code):
    # On Windows, PowerShell closes immediately after the program exits. If the program exits
    # due to an error, the user is not able to see the error unless they check the log file.
    # This method is used to allow the user to view any errors and inform them of where they
    # can find more information about what went wrong.

    if exit_code != 0:
        print('Check the log file (\'data/logs/debug.log\' by default) for more information')
        print('Press ENTER to exit')
        input()
    sys.exit(exit_code)


def print_help_information():
   print('Usage: ./spautomod [option]')
   print('Options:')
   print(' -l, --loop   Run in loop mode: run in continuous cycles until asked to quit')
   print(' --rdc        Restore default configuration file and quit')
   print(' -h, --help   Show help information for command usage and quit')


if __name__ == '__main__':
    main()
