import os, json
from dynaconf import Dynaconf
from dynaconf.loaders.toml_loader import write
from typing import Union

class Settings:
    def __init__(self) -> None:
        self.config: Union[Dynaconf, None] = None
        path_file = os.path.realpath(__file__)
        dir_path = os.path.dirname(path_file)
        self.path_file = f'{dir_path}\\settings.toml'

    def read_conf(self):
        self.config: Dynaconf = Dynaconf(
            settings_files=[self.path_file],
                )
    
    def update_settings(self, data):
        write(self.path_file, data)
        self.config = Dynaconf(
            settings_files=[self.path_file],
                )
        
    def get_conection_database(self, type_db):
        try:
            if type_db == 'bot':
                database_conf = self.config.Database_bot
            elif type_db == 'info':
                database_conf = self.config.Database_info
        except (IndexError, AttributeError):        
            user = os.environ.get('postgreuser')
            user = json.loads(user)
            database_conf['user'], database_conf['password'] = user
        return database_conf

settings = Settings()
settings.read_conf()