import os
import sys
import json
import uuid
import hashlib
from logger import logging


class ResetterMachineIDs:
    def __init__(self):
        if sys.platform == "win32":
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("not.set.environment.variable.APPDATA")
            self.db_path = os.path.join(
                appdata, "Cursor", "User", "globalStorage", "storage.json"
            )
        elif sys.platform == "darwin":
            self.db_path = os.path.abspath(
                os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
                )
            )
        elif sys.platform == "linux":
            self.db_path = os.path.abspath(
                os.path.expanduser("~/.config/Cursor/User/globalStorage/storage.json")
            )
        else:
            raise NotImplementedError('os.not.supported: {sys.platform}')

    def generate_new_ids(self):
        dev_device_id = str(uuid.uuid4())
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"

        return {
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.machineId": machine_id,
            "telemetry.sqmId": sqm_id,
        }

    def reset_machine_ids(self):
        try:
            logging.info('resetting.machine.ids')
            
            if not os.path.exists(self.db_path):
                logging.error('config.not.exists')
                return False

            if not os.access(self.db_path, os.R_OK | os.W_OK):
                logging.error('config.not.accessible')
                logging.warning('read.write.permission.required')
                return False

            logging.info('reading.config')
            with open(self.db_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            logging.info('generating.new.ids')
            new_ids = self.generate_new_ids()

            config.update(new_ids)

            logging.info('saving.new.config')
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            logging.info('machine.ids.reset.success')
            logging.info('machine.ids.reset.info:')
            for key, value in new_ids.items():
                logging.info('key: %s, value: %s' % (key, value))

            return True

        except PermissionError as e:
            logging.error('admin.permission.required')
            return False
        except Exception as e:
            logging.error(f'error.resetting.machine.ids: {str(e)}')

            return False


if __name__ == "__main__":
    resetter = ResetterMachineIDs()
    resetter.reset_machine_ids()