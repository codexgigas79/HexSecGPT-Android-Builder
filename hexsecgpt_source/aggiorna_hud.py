from pathlib import Path
import shutil

p = Path("HexSecGPT.py")
s = p.read_text(encoding="utf-8")

start = s.index("# --- UI / TUI Class ---")
end = s.index("# --- AI Logic Class ---", start)

backup = Path("HexSecGPT_pre_cyberhud.py")
if not backup.exists():
    shutil.copy2(p, backup)

new_ui = r'''# --- UI / TUI Class ---
class UI:
    """Cyber HUD Interface"""

    def __init__(self):
        self.console = Console(
            color_system="truecolor",
            highlight=False
        )

    def clear(self):
        self.console.clear()

    def banner(self):
        self.clear()

        title = Text()
        title.append("H E X ", style="bold bright_cyan")
        title.append("S E C ", style="bold cyan")
        title.append("G P T", style="bold bright_white")

        subtitle = Text(
            "ADVANCED CYBER SECURITY SYSTEM",
            style="bold bright_blue"
        )

        header = Table.grid(expand=True)
        header.add_column(justify="center")
        header.add_row(title)
        header.add_row(subtitle)

        self.console.print(
            Panel(
                Align.center(header, vertical="middle"),
                title="[bold bright_cyan]◈ HEXSEC COMMAND CENTER ◈[/]",
                subtitle="[dim cyan]SECURE CONNECTION // SYSTEM ONLINE[/]",
                border_style="bright_cyan",
                padding=(1, 2)
            )
        )

        status = Table.grid(expand=True, padding=(0, 2))
        status.add_column(ratio=1)
        status.add_column(ratio=1)
        status.add_column(ratio=1)

        status.add_row(
            "[bold bright_green]● ONLINE[/]",
            "[bold bright_cyan]● AI ENGINE[/]",
            "[bold bright_blue]● SECURITY MODE[/]"
        )
        status.add_row(
            "[dim]SYSTEM READY[/]",
            "[dim]NEURAL LINK[/]",
            "[dim]AUTHORIZED USE[/]"
        )

        self.console.print(
            Panel(
                status,
                title="[bold cyan]SYSTEM TELEMETRY[/]",
                border_style="blue"
            )
        )

        self.console.print(
            Align.center(
                Text(
                    "Developed by HexSecTeam  //  "
                    + time.strftime("%Y-%m-%d  %H:%M:%S"),
                    style="dim cyan"
                )
            )
        )
        self.console.print()

    def main_menu(self):
        table = Table(
            show_header=True,
            header_style="bold bright_cyan",
            border_style="cyan",
            expand=True
        )

        table.add_column("ID", style="bold bright_blue", width=8)
        table.add_column("COMMAND", style="bold white")
        table.add_column("DESCRIPTION", style="dim white")

        table.add_row("01", "INITIALIZE UPLINK", "Start AI conversation")
        table.add_row("02", "SECURITY KEYS", "Configure API connection")
        table.add_row("03", "SYSTEM MANIFESTO", "System information")
        table.add_row("04", "TERMINATE", "Close session")

        self.console.print(
            Panel(
                table,
                title="[bold bright_cyan]◈ MAIN CONTROL PANEL ◈[/]",
                subtitle="[dim]Select an operation[/]",
                border_style="bright_cyan",
                padding=(1, 2)
            )
        )

    def show_msg(self, title: str, content: str, color: str = "white"):
        self.console.print(
            Panel(
                content,
                title=f"[bold bright_cyan]◈ {title.upper()}[/]",
                border_style=color,
                padding=(1, 2)
            )
        )

    def get_input(self, label: str = "COMMAND") -> str:
        prompt_style = Config.Colors.USER_PROMPT

        self.console.print(
            f"[{prompt_style}]╭── [{label.upper()}][/]"
        )
        return self.console.input(
            f"[bold bright_cyan]╰─➤ [/]"
        )

    def stream_markdown(self, title: str, content_generator):
        full_response = ""

        with Live(
            Panel(
                Spinner(
                    "dots",
                    text="[bright_cyan]Processing neural response...[/]"
                ),
                title=f"[bold bright_cyan]◈ {title} ◈[/]",
                border_style="bright_cyan"
            ),
            console=self.console,
            refresh_per_second=12,
            transient=False
        ) as live:

            for chunk in content_generator:
                full_response += chunk

                display_text = (
                    full_response
                    .replace("[HexSecGPT]:", "")
                    .replace("[HexSecGPT]", "")
                    .strip()
                )

                if not display_text:
                    display_text = "..."

                live.update(
                    Panel(
                        Markdown(
                            display_text,
                            code_theme=Config.CODE_THEME
                        ),
                        title=f"[bold bright_cyan]◈ {title}[/]",
                        subtitle="[dim cyan]NEURAL LINK ACTIVE[/]",
                        border_style="bright_cyan",
                        padding=(1, 2)
                    )
                )

            display_text = (
                full_response
                .replace("[HexSecGPT]:", "")
                .replace("[HexSecGPT]", "")
                .strip()
            )

            live.update(
                Panel(
                    Markdown(
                        display_text or "Nessuna risposta ricevuta.",
                        code_theme=Config.CODE_THEME
                    ),
                    title=f"[bold bright_green]◈ {title} ✓[/]",
                    subtitle="[dim green]TRANSMISSION COMPLETE[/]",
                    border_style="bright_green",
                    padding=(1, 2)
                )
            )

'''

s = s[:start] + new_ui + s[end:]
p.write_text(s, encoding="utf-8")

print("CYBER HUD installato correttamente.")
print("Backup:", backup)
