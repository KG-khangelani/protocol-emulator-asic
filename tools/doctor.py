"""Report prerequisites; never treat missing tools as installed."""
import importlib.util
import platform
import shutil
import subprocess

print("Python:", platform.python_version())
for executable in ("git", "make", "iverilog", "vvp", "cocotb-config", "yosys", "docker"):
    found = shutil.which(executable)
    print(f"{executable}: {found or 'MISSING'}")
for module in ("cocotb", "yaml"):
    print(f"Python {module}: {'available' if importlib.util.find_spec(module) else 'MISSING'}")
for cmd in (["git", "--version"], ["yosys", "-V"]):
    if shutil.which(cmd[0]):
        subprocess.run(cmd, check=False)
print("RTL needs Icarus + cocotb. Generic synthesis needs Yosys. Full GDS uses the CMOS5L workflow.")
