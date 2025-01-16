import psutil
from logger import logging  
import time

def ExitCursor(timeout=5):
    try:
        logging.info("exit.cursor")
        cursor_processes = []
        path_cursor = ''
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in ['cursor.exe', 'cursor']:
                    try:
                        if not path_cursor:
                            raw_path = proc.exe()
                            if raw_path and '.app' in raw_path:
                                path_cursor = raw_path[:raw_path.find('.app') + 4]
                            else:
                                path_cursor = raw_path
                            logging.info(f'found.cursor {path_cursor}')
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        logging.warning('exit.cursor.path.error')
                    cursor_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not cursor_processes:
            logging.info("not.found.cursor")
            return True, path_cursor

        for proc in cursor_processes:
            try:
                if proc.is_running():
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        start_time = time.time()
        while time.time() - start_time < timeout:
            still_running = []
            for proc in cursor_processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not still_running:
                logging.info("exit.cursor.success")
                return True, path_cursor
                
            time.sleep(0.5)
            
        if still_running:
            process_list = ", ".join([str(p.pid) for p in still_running])
            logging.warning(f'exit.cursor.timeout {process_list}')
            return False, path_cursor
            
        return True, path_cursor

    except Exception as e:
        logging.error(f'exit.cursor.error {str(e)}')
        return False, ''

if __name__ == "__main__":
    success, path = ExitCursor()
    if path:
        logging.info(f'exit.cursor.path {path}')
