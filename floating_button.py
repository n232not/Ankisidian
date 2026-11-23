"""
Ankisidian - Draggable Floating Button
A sleek, draggable action button that floats over Anki's window,
allowing one-click transfer of the active note to Obsidian.
Supports click-to-export, dragging anywhere, and position persistence.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

try:
    from aqt.qt import (
        QColor,
        QCursor,
        QGraphicsDropShadowEffect,
        QMenu,
        QMouseEvent,
        QPoint,
        QPushButton,
        Qt,
    )
except ImportError:
    # Fallback / mock for testing without Anki/PyQt
    QPushButton = object  # type: ignore
    QPoint = object  # type: ignore


class DraggableObsidianButton(QPushButton):
    """
    A floating, draggable button that hovers on top of Anki's main window.
    Clicking it transfers the current note.
    Dragging it allows the user to place it anywhere on screen.
    """

    def __init__(
        self,
        parent: Any,
        on_click_callback: Callable[[], None],
        on_settings_callback: Callable[[], None],
        on_hide_callback: Callable[[], None],
        config: Dict[str, Any],
        on_position_changed: Optional[Callable[[int, int], None]] = None,
    ):
        super().__init__(parent)
        self.on_click_callback = on_click_callback
        self.on_settings_callback = on_settings_callback
        self.on_hide_callback = on_hide_callback
        self.on_position_changed = on_position_changed
        self.config = config

        self._drag_start_pos: Optional[QPoint] = None
        self._button_start_pos: Optional[QPoint] = None
        self._is_dragging = False

        self._init_ui()

    def _init_ui(self):
        label = self.config.get("button_label", "📓 To Obsidian")
        self.setText(label)
        self.setToolTip(
            "Transfer active note to Obsidian\n• Click: Transfer now\n• Drag: Move anywhere\n• Right-click: Menu & Settings"
        )

        # Set cursor to pointing hand
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, "CursorShape") else Qt.PointingHandCursor))

        # Modern styling matching Obsidian theme
        self.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9);
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 7px 14px;
                border-radius: 16px;
                border: 1px solid #7c3aed;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9333ea, stop:1 #581c87);
                border: 1px solid #a855f7;
            }
            QPushButton:pressed {
                background-color: #4c1d95;
            }
            """
        )

        # Drop shadow for floating effect
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(14)
            shadow.setColor(QColor(0, 0, 0, 110))
            shadow.setOffset(0, 3)
            self.setGraphicsEffect(shadow)
        except Exception:
            pass

        self.adjustSize()

        # Restore saved position
        saved_pos = self.config.get("button_position", [20, 80])
        if isinstance(saved_pos, (list, tuple)) and len(saved_pos) == 2:
            self.move(int(saved_pos[0]), int(saved_pos[1]))
        else:
            self.move(20, 80)

        self.show()
        self.raise_()

    def _get_event_global_pos(self, event: QMouseEvent) -> QPoint:
        if hasattr(event, "globalPosition"):
            return event.globalPosition().toPoint()
        return event.globalPos()

    def mousePressEvent(self, event: QMouseEvent):
        left_button = Qt.MouseButton.LeftButton if hasattr(Qt, "MouseButton") else Qt.LeftButton
        if event.button() == left_button:
            self._drag_start_pos = self._get_event_global_pos(event)
            self._button_start_pos = self.pos()
            self._is_dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        left_button = Qt.MouseButton.LeftButton if hasattr(Qt, "MouseButton") else Qt.LeftButton
        if (event.buttons() & left_button) and self._drag_start_pos and self._button_start_pos:
            curr_pos = self._get_event_global_pos(event)
            delta = curr_pos - self._drag_start_pos
            if delta.manhattanLength() > 4:
                self._is_dragging = True
                new_x = self._button_start_pos.x() + delta.x()
                new_y = self._button_start_pos.y() + delta.y()

                # Clamp to parent boundary if parent exists
                parent = self.parentWidget()
                if parent:
                    new_x = max(0, min(new_x, parent.width() - self.width()))
                    new_y = max(0, min(new_y, parent.height() - self.height()))

                self.move(new_x, new_y)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        left_button = Qt.MouseButton.LeftButton if hasattr(Qt, "MouseButton") else Qt.LeftButton
        if event.button() == left_button:
            if not self._is_dragging:
                # Normal click: trigger transfer
                super().mouseReleaseEvent(event)
                if self.on_click_callback:
                    self.on_click_callback()
            else:
                # Drag finished: save new position
                self._is_dragging = False
                if self.on_position_changed:
                    self.on_position_changed(self.x(), self.y())
                return
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """Right-click menu for quick access to actions and settings."""
        menu = QMenu(self)
        export_action = menu.addAction("📓 Transfer Note to Obsidian")
        export_action.triggered.connect(self.on_click_callback)

        menu.addSeparator()
        settings_action = menu.addAction("⚙️ Ankisidian Settings...")
        settings_action.triggered.connect(self.on_settings_callback)

        hide_action = menu.addAction("👁️ Hide Floating Button")
        hide_action.triggered.connect(self.on_hide_callback)

        pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        menu.exec(pos)
