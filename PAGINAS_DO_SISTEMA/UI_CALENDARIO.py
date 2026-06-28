# -*- coding: utf-8 -*-
from __future__ import annotations

import calendar as _cal
from datetime import date, datetime, timedelta
import platform
import re
from typing import Callable

import customtkinter as ctk


IS_MAC = platform.system() == "Darwin"
_OPEN_CALENDAR_POPUPS = []


def _widget_exists(widget) -> bool:
    try:
        return bool(widget and widget.winfo_exists())
    except Exception:
        return False


def _get_root(widget):
    try:
        return widget.winfo_toplevel()
    except Exception:
        return widget


def _popup_owner_root(popup):
    try:
        return getattr(popup, "_ui_calendar_owner_root", None)
    except Exception:
        return None


def _destroy_popup(popup):
    try:
        if _widget_exists(popup):
            popup.destroy()
    except Exception:
        pass


def _unregister_popup(popup):
    try:
        if popup in _OPEN_CALENDAR_POPUPS:
            _OPEN_CALENDAR_POPUPS.remove(popup)
    except Exception:
        pass


def _release_topmost(popup):
    try:
        if _widget_exists(popup):
            popup.attributes("-topmost", False)
    except Exception:
        pass


def fechar_calendarios(owner=None):
    """Fecha popups de calendario abertos antes de trocar de pagina/janela."""
    root = _get_root(owner) if owner is not None else None
    for popup in list(_OPEN_CALENDAR_POPUPS):
        if not _widget_exists(popup):
            try:
                _OPEN_CALENDAR_POPUPS.remove(popup)
            except ValueError:
                pass
            continue
        popup_root = _popup_owner_root(popup) or _get_root(popup)
        if root is None or popup_root is root:
            _destroy_popup(popup)
            try:
                _OPEN_CALENDAR_POPUPS.remove(popup)
            except ValueError:
                pass
    if owner is not None:
        for obj in (owner, root):
            try:
                obj._ui_calendar_popup = None
            except Exception:
                pass


def _read_date(entry) -> date:
    text = ""
    try:
        text = (entry.get() or "").strip()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except Exception:
            pass
    return date.today()


def _output_format(entry, output_format: str = "auto") -> str:
    if output_format and output_format != "auto":
        return output_format
    try:
        text = (entry.get() or "").strip()
    except Exception:
        text = ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return "%Y-%m-%d"
    return "%d/%m/%Y"


def _get_color(owner, name: str, fallback: str) -> str:
    return getattr(owner, name, fallback)


def _as_hex(color) -> str | None:
    if isinstance(color, (tuple, list)) and color:
        color = color[-1]
    color = str(color or "").strip()
    if re.match(r"^#[0-9a-fA-F]{6}$", color):
        return color.upper()
    return None


def _rgb(color: str) -> tuple[int, int, int] | None:
    color = _as_hex(color)
    if not color:
        return None
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _luma(color: str) -> float:
    value = _rgb(color)
    if not value:
        return 0
    r, g, b = value
    return r * 0.299 + g * 0.587 + b * 0.114


def _distance(a: str, b: str) -> float:
    rgb_a = _rgb(a)
    rgb_b = _rgb(b)
    if not rgb_a or not rgb_b:
        return 255
    return sum((x - y) ** 2 for x, y in zip(rgb_a, rgb_b)) ** 0.5


def _text_for(bg_color: str, fallback: str = "#111827") -> str:
    color = _as_hex(bg_color)
    if not color:
        return fallback
    return "#111827" if _luma(color) > 170 else "#FFFFFF"


def _darken(color: str, amount: int = 28) -> str:
    value = _rgb(color)
    if not value:
        return color
    r, g, b = value
    return f"#{max(0, r - amount):02X}{max(0, g - amount):02X}{max(0, b - amount):02X}"


def _is_neutral(color: str) -> bool:
    value = _rgb(color)
    if not value:
        return True
    r, g, b = value
    return max(r, g, b) - min(r, g, b) < 32


def _is_green(color: str) -> bool:
    value = _rgb(color)
    if not value:
        return False
    r, g, b = value
    return g >= r + 18 and g >= b + 8


def _choose_accent(owner, surface: str) -> str:
    green_default = "#15803D"
    for name in ("cor_sucesso", "cor_selecao", "cor_destaque", "cor_primaria"):
        color = _as_hex(_get_color(owner, name, ""))
        if color and _is_green(color) and _distance(color, surface) > 80 and _luma(color) < 235:
            return color
    return green_default


def _month_name(month: int) -> str:
    meses = (
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    )
    return meses[month] if 1 <= month <= 12 else _cal.month_name[month]


def abrir_calendario(
    owner,
    entry,
    *,
    output_format: str = "auto",
    on_select: Callable[[date | None], None] | None = None,
    auto_close_ms: int = 3000,
):
    root = _get_root(owner)
    try:
        old = getattr(owner, "_ui_calendar_popup", None)
        if old is not None and old.winfo_exists():
            old.destroy()
    except Exception:
        pass
    try:
        old_root = getattr(root, "_ui_calendar_popup", None)
        if old_root is not None and old_root is not getattr(owner, "_ui_calendar_popup", None):
            if old_root.winfo_exists():
                old_root.destroy()
    except Exception:
        pass

    selected = _read_date(entry)
    current = {"year": selected.year, "month": selected.month}
    selected_holder = {"date": selected}

    owner_bg = _as_hex(_get_color(owner, "cor_fundo", "#F8FAFC")) or "#F8FAFC"
    dark_mode = _luma(owner_bg) < 90
    bg = "#1F2937" if dark_mode else "#F3F4F6"
    panel = "#111827" if dark_mode else "#FFFFFF"
    grid_panel = "#1F2937" if dark_mode else "#F9FAFB"
    text = "#F9FAFB" if dark_mode else "#111827"
    muted_text = "#9CA3AF" if dark_mode else "#6B7280"
    border = "#374151" if dark_mode else "#B7BBC3"
    header_bg = "#27272A" if dark_mode else "#3F3F46"
    header_hover = "#52525B"
    weekday_bg = "#374151" if dark_mode else "#D1D5DB"
    outside_bg = "#374151" if dark_mode else "#D6D6D6"
    day_bg = "#111827" if dark_mode else "#FFFFFF"
    day_hover = "#374151" if dark_mode else "#E5E7EB"
    accent = _choose_accent(owner, panel)
    if _is_neutral(accent):
        accent = "#15803D"
    hover = _as_hex(_get_color(owner, "cor_hover", _darken(accent))) or _darken(accent)
    if _is_neutral(hover) or not _is_green(hover) or _distance(hover, panel) < 70:
        hover = _darken(accent)
    button_text = _text_for(accent, text)

    top = ctk.CTkToplevel(root)
    try:
        top.withdraw()
    except Exception:
        pass
    try:
        top._ui_calendar_owner_root = root
        owner._ui_calendar_popup = top
        root._ui_calendar_popup = top
    except Exception:
        pass
    _OPEN_CALENDAR_POPUPS.append(top)
    top.title("Calendário")
    top.resizable(False, False)
    top.configure(fg_color=bg)
    try:
        top.protocol("WM_DELETE_WINDOW", lambda: _destroy_popup(top))
    except Exception:
        pass
    try:
        top.bind("<Destroy>", lambda _event, popup=top: _unregister_popup(popup), add="+")
    except Exception:
        pass
    if IS_MAC:
        try:
            top.overrideredirect(True)
        except Exception:
            pass

    width, height = 320, 365
    try:
        owner.update_idletasks()
        top.update_idletasks()
        x = entry.winfo_rootx()
        y = entry.winfo_rooty() + entry.winfo_height() + 6
        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if x + width > sw:
            x = sw - width - 10
        if y + height > sh:
            y = entry.winfo_rooty() - height - 6
        top.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
    except Exception:
        top.geometry(f"{width}x{height}")

    try:
        top.transient(root)
        if IS_MAC:
            top.attributes("-topmost", True)
        top.lift(root)
        if not IS_MAC:
            top.focus_set()
    except Exception:
        pass

    inside = {"value": False}
    close_after = {"id": None}

    def pointer_inside() -> bool:
        try:
            px = top.winfo_pointerx()
            py = top.winfo_pointery()
            tx = top.winfo_rootx()
            ty = top.winfo_rooty()
            tw = top.winfo_width()
            th = top.winfo_height()
            return tx <= px <= tx + tw and ty <= py <= ty + th
        except Exception:
            return False

    def cancel_auto_close():
        job = close_after.get("id")
        if job:
            try:
                top.after_cancel(job)
            except Exception:
                pass
        close_after["id"] = None

    def schedule_auto_close():
        cancel_auto_close()

        def close_if_outside():
            close_after["id"] = None
            if not inside["value"] and not pointer_inside():
                try:
                    top.destroy()
                except Exception:
                    pass

        close_after["id"] = top.after(auto_close_ms, close_if_outside)

    def mark_inside(_event=None):
        inside["value"] = True
        cancel_auto_close()

    def mark_outside(_event=None):
        inside["value"] = False
        schedule_auto_close()

    top.bind("<Enter>", mark_inside, add="+")
    top.bind("<Leave>", mark_outside, add="+")
    top.bind("<FocusOut>", mark_outside, add="+")

    nav = ctk.CTkFrame(top, fg_color=header_bg, border_width=1, border_color=border, corner_radius=4)
    nav.pack(fill="x", padx=10, pady=(10, 0))
    month_box = ctk.CTkFrame(nav, fg_color="transparent")
    month_box.pack(side="left", fill="x", expand=True, padx=(4, 0), pady=4)
    year_box = ctk.CTkFrame(nav, fg_color="transparent")
    year_box.pack(side="right", padx=(0, 4), pady=4)

    month_title = ctk.CTkLabel(
        month_box, text="", width=128, text_color="#FFFFFF",
        font=ctk.CTkFont(size=13, weight="bold")
    )
    year_title = ctk.CTkLabel(
        year_box, text="", width=58, text_color="#FFFFFF",
        font=ctk.CTkFont(size=13, weight="bold")
    )

    grid = ctk.CTkFrame(top, fg_color=grid_panel, border_width=1, border_color=border, corner_radius=0)
    grid.pack(fill="both", expand=True, padx=10, pady=(0, 8))
    footer = ctk.CTkFrame(top, fg_color=bg)
    footer.pack(fill="x", padx=10, pady=(0, 10))

    def apply_date(chosen):
        try:
            entry.delete(0, "end")
            if chosen is not None:
                entry.insert(0, chosen.strftime(_output_format(entry, output_format)))
        except Exception:
            pass
        if on_select:
            on_select(chosen)
        try:
            top.destroy()
        except Exception:
            pass

    def select_date(chosen: date):
        selected_holder["date"] = chosen
        current["year"] = chosen.year
        current["month"] = chosen.month
        draw()

    def move_month(delta: int):
        month_new = current["month"] + delta
        year_new = current["year"]
        if month_new > 12:
            month_new = 1
            year_new += 1
        elif month_new < 1:
            month_new = 12
            year_new -= 1
        current["month"] = month_new
        current["year"] = year_new
        draw()

    def move_year(delta: int):
        current["year"] += delta
        draw()

    ctk.CTkButton(
        month_box, text="<", width=24, height=24, fg_color=header_bg,
        hover_color=header_hover, text_color="#FFFFFF", corner_radius=3,
        command=lambda: move_month(-1)
    ).pack(side="left")
    month_title.pack(side="left", expand=True)
    ctk.CTkButton(
        month_box, text=">", width=24, height=24, fg_color=header_bg,
        hover_color=header_hover, text_color="#FFFFFF", corner_radius=3,
        command=lambda: move_month(1)
    ).pack(side="left")

    ctk.CTkButton(
        year_box, text="<", width=22, height=24, fg_color=header_bg,
        hover_color=header_hover, text_color="#FFFFFF", corner_radius=3,
        command=lambda: move_year(-1)
    ).pack(side="left")
    year_title.pack(side="left")
    ctk.CTkButton(
        year_box, text=">", width=22, height=24, fg_color=header_bg,
        hover_color=header_hover, text_color="#FFFFFF", corner_radius=3,
        command=lambda: move_year(1)
    ).pack(side="left")

    weekdays = ("dom.", "seg.", "ter.", "qua.", "qui.", "sex.", "sáb.")

    def draw():
        for child in grid.winfo_children():
            child.destroy()
        month_title.configure(text=_month_name(current["month"]))
        year_title.configure(text=str(current["year"]))

        for col, label in enumerate(weekdays):
            ctk.CTkLabel(
                grid, text=label, width=40, height=24, fg_color=weekday_bg,
                text_color=text, corner_radius=0, font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=0, column=col, padx=0, pady=0, sticky="nsew")

        weeks = _cal.Calendar(firstweekday=6).monthdatescalendar(current["year"], current["month"])
        while len(weeks) < 6:
            start_next = weeks[-1][-1] + timedelta(days=1)
            weeks.append([start_next + timedelta(days=i) for i in range(7)])

        for row_idx, week in enumerate(weeks[:6], start=1):
            for col, day_value in enumerate(week):
                is_current_month = day_value.month == current["month"]
                is_selected = selected_holder["date"] == day_value
                fg = accent if is_selected else (day_bg if is_current_month else outside_bg)
                fg_hover = hover if is_selected else day_hover
                txt = button_text if is_selected else (text if is_current_month else muted_text)
                cell = ctk.CTkFrame(
                    grid,
                    width=40,
                    height=36,
                    fg_color=fg,
                    border_width=1,
                    border_color=border,
                    corner_radius=0,
                )
                cell.grid(row=row_idx, column=col, padx=0, pady=0, sticky="nsew")
                cell.grid_propagate(False)
                label_day = ctk.CTkLabel(
                    cell,
                    text=str(day_value.day),
                    text_color=txt,
                    fg_color="transparent",
                    font=ctk.CTkFont(size=13),
                )
                label_day.place(relx=0.5, rely=0.5, anchor="center")

                def on_enter(_event=None, widget=cell, color=fg_hover):
                    widget.configure(fg_color=color)

                def on_leave(_event=None, widget=cell, color=fg):
                    widget.configure(fg_color=color)

                def on_click(_event=None, chosen=day_value):
                    select_date(chosen)

                for widget in (cell, label_day):
                    widget.bind("<Enter>", on_enter, add="+")
                    widget.bind("<Leave>", on_leave, add="+")
                    widget.bind("<Button-1>", on_click, add="+")

        def bind_recursive(widget):
            widget.bind("<Enter>", mark_inside, add="+")
            widget.bind("<Leave>", mark_outside, add="+")
            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(top)

    ctk.CTkButton(
        footer, text="Limpar", width=90, height=34, fg_color="#6B7280",
        hover_color="#4B5563", text_color="#FFFFFF", corner_radius=6,
        command=lambda: apply_date(None)
    ).pack(side="left", expand=True, fill="x", padx=(0, 4))
    ctk.CTkButton(
        footer, text="Hoje", width=90, height=34, fg_color=accent,
        hover_color=hover, text_color=button_text, corner_radius=6,
        command=lambda: select_date(date.today())
    ).pack(side="left", expand=True, fill="x", padx=4)
    ctk.CTkButton(
        footer, text="Confirmar", width=100, height=34, fg_color=accent,
        hover_color=hover, text_color=button_text, corner_radius=6,
        command=lambda: apply_date(selected_holder["date"])
    ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    draw()
    try:
        top.deiconify()
        top.lift(root)
        if IS_MAC:
            top.after(250, lambda popup=top: _release_topmost(popup))
    except Exception:
        pass
    schedule_auto_close()
    return top


def vincular_calendario(owner, entry, *, output_format: str = "auto", on_select=None):
    def open_calendar(_event=None):
        try:
            if entry.cget("state") == "disabled":
                return None
        except Exception:
            pass
        return abrir_calendario(owner, entry, output_format=output_format, on_select=on_select)

    entry.bind("<Button-1>", open_calendar, add="+")
    entry.bind("<Double-Button-1>", open_calendar, add="+")
    return entry


def instalar_auto_fechamento(popup, *, auto_close_ms: int = 3000):
    inside = {"value": False}
    close_after = {"id": None}

    def pointer_inside() -> bool:
        try:
            px = popup.winfo_pointerx()
            py = popup.winfo_pointery()
            x = popup.winfo_rootx()
            y = popup.winfo_rooty()
            return x <= px <= x + popup.winfo_width() and y <= py <= y + popup.winfo_height()
        except Exception:
            return False

    def cancel():
        job = close_after.get("id")
        if job:
            try:
                popup.after_cancel(job)
            except Exception:
                pass
        close_after["id"] = None

    def schedule(_event=None):
        inside["value"] = False
        cancel()

        def close_if_needed():
            close_after["id"] = None
            if not inside["value"] and not pointer_inside():
                try:
                    popup.destroy()
                except Exception:
                    pass

        close_after["id"] = popup.after(auto_close_ms, close_if_needed)

    def enter(_event=None):
        inside["value"] = True
        cancel()

    def bind_recursive(widget):
        widget.bind("<Enter>", enter, add="+")
        widget.bind("<Leave>", schedule, add="+")
        for child in widget.winfo_children():
            bind_recursive(child)

    bind_recursive(popup)
    popup.bind("<FocusOut>", schedule, add="+")
    schedule()
