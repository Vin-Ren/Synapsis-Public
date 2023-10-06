from threading import Thread
from automators.data_structs import Config
from app import App
import logging
from logger import setupLogger

logger = logging.getLogger()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="A runner for Synapsis.")
    
    parser.add_argument('-c', '--config-file', dest='config_file', default='config.yaml', help='Set the config file to configure the app.')
    parser.add_argument('--log-file', dest='log_file', default='logs.log', help='Set the log file')
    parser.add_argument('--dev-mode', dest='dev_mode', action='store_true', help='Sets necessary environment for interactive development. Use in development only, with "py -i main.py --dev-mode".')
    
    args = parser.parse_args()
    if args.dev_mode:
        config = Config.from_file('config.test.yaml')
    else:
        config = Config.from_file(args.config_file)
        
    setupLogger(**config.get('logging', Config()))
    
    App.configure(config)
    app = App()
    
    if args.dev_mode:
        import atexit
        app_thread = Thread(target=app.run, name='App-Thread', daemon=True)
        app_thread.start()
        def logger_spacing():
            logger.info(\
                "\n"*4 + "".center(150,'-') + "\n" + \
                " END OF SESSION ".center(150,'-') + \
                "\n" + "".center(150,'-') + "\n"*5 \
            )
        atexit.register(logger_spacing)
    else:
        app.run()
