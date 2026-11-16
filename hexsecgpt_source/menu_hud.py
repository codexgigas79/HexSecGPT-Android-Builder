from pathlib import Path
import shutil

p = Path("HexSecGPT.py")
s = p.read_text(encoding="utf-8")

start = s.index("    def main_menu(self):")
end = s.index("    def show_msg(", start)

backup = Path("HexSecGPT_pre_menu_mobile.py")
if not backup.exists():
    shutil.copy2(p, backup)

new_method = '''    def main_menu(self):
        grid = Table.grid(expand=True, padding=(1, 1))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)

        grid.add_row(
            "[bold bright_cyan]01[/]  INITIALIZE UPLINK",
            "[bold bright_cyan]02[/]  SECURITY KEYS"
        )
        grid.add_row(
            "[bold bright_cyan]03[/]  SYSTEM INFO",
            "[bold bright_red]04[/]  TERMINATE"
        )

        self.console.print(
            Panel(
                grid,
                title="[bold bright_cyan]◈ MAIN CONTROL ◈[/]",
                subtitle="[dim cyan]SELECT OPERATION[/]",
                border_style="bright_cyan",
                padding=(0, 1)
            )
        )

'''

s = s[:start] + new_method + s[end:]
p.write_text(s, encoding="utf-8")

print("Menu mobile Cyber HUD aggiornato.")
print("Backup:", backup)
