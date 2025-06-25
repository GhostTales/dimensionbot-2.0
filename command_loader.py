import os
from cogs.common.misc import color_string

async def load_cogs(bot):
    for file in os.listdir("cogs"):
            if file.endswith(".py") and file != "__init__.py":
                module_name = file[:-3]  # Strip '.py'
                full_module = f"cogs.{module_name}"
                try:
                    await bot.load_extension(full_module)  # Await here
                    print(f"{color_string("Loaded extension:", "green")} {color_string(f"{full_module}", "yellow")}:")
                except Exception as e:
                    print(f"{color_string("Failed to load extension", "red")} {color_string(f"{full_module}", "yellow")}: {color_string(f"{e}", "red")}")
