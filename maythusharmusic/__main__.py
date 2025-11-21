import asyncio
import importlib
from sys import argv
from pyrogram import idle
from pyrogram.errors import RPCError, FloodWait, ConnectionError as PyrogramConnectionError
from pytgcalls.exceptions import NoActiveGroupCall

import config
from maythusharmusic import LOGGER, app, userbot, YouTube
from maythusharmusic.core.call import Hotty
from maythusharmusic.misc import sudo
from maythusharmusic.plugins import ALL_MODULES
from maythusharmusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()
    
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass

    # Auto-reconnect system
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await app.start()
            LOGGER(__name__).info("App started successfully!")
            
            for all_module in ALL_MODULES:
                importlib.import_module("maythusharmusic.plugins" + all_module)
            LOGGER("maythusharmusic.plugins").info("Successfully Imported Modules...")
            
            await userbot.start()
            await Hotty.start()
            
            try:
                await Hotty.stream_call("https://graph.org/file/e999c40cb700e7c684b75.mp4")
            except NoActiveGroupCall:
                LOGGER("maythusharmusic").error(
                    "Please turn on the videochat of your log group\channel.\n\nStopping Bot..."
                )
                exit()
            except Exception as e:
                LOGGER(__name__).warning(f"Stream call error: {e}")
                pass
            
            await Hotty.decorators()
            LOGGER("maythusharmusic").info(
                "Bot started successfully! Join @sasukevipmusicbot for support"
            )
            
            # YouTube Cache Pre-load
            LOGGER(__name__).info("Loading YouTube Cache...")
            try:
                await YouTube.load_cache() 
            except Exception as e:
                LOGGER(__name__).error(f"YouTube Cache load failed: {e}")
            
            # Successful connection
            retry_count = 0
            break
            
        except (PyrogramConnectionError, ConnectionError, OSError) as e:
            retry_count += 1
            LOGGER(__name__).error(f"Connection Error (Attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                wait_time = retry_count * 10
                LOGGER(__name__).info(f"Reconnecting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                LOGGER(__name__).error("Max retries reached. Exiting...")
                exit()
                
        except FloodWait as e:
            LOGGER(__name__).warning(f"Flood wait: {e.value} seconds")
            await asyncio.sleep(e.value)
            
        except RPCError as e:
            LOGGER(__name__).error(f"RPC Error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(30)
            else:
                LOGGER(__name__).error("Max retries reached. Exiting...")
                exit()
                
        except Exception as e:
            LOGGER(__name__).error(f"Unexpected error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(30)
            else:
                LOGGER(__name__).error("Max retries reached. Exiting...")
                exit()

async def main():
    """Main function with auto-restart"""
    while True:
        try:
            await init()
            await idle()
            
        except KeyboardInterrupt:
            LOGGER(__name__).info("Bot stopped by user")
            break
        except Exception as e:
            LOGGER(__name__).error(f"Main loop error: {e}")
            LOGGER(__name__).info("Restarting bot in 10 seconds...")
            await asyncio.sleep(10)
        finally:
            try:
                await app.stop()
                await userbot.stop()
                await Hotty.stop()
            except:
                pass

if __name__ == "__main__":
    asyncio.run(main())
