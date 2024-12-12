use iced::widget::scrollable;
use crate::messages::LogType;
use crate::messages::Choice;

#[derive(Debug)]
struct ScrollState {
    viewport: Option<scrollable::Viewport>,
    scrolled_to_bottom: bool,
}

impl Default for ScrollState {
    fn default() -> Self {
        Self {
            viewport: None,
            scrolled_to_bottom: true,
        }
    }
}

#[derive(Debug, Clone)]
struct LogMessage {
    content: String,
    log_type: LogType,
}

#[derive(Debug, Clone)]
struct DropdownState {
    selected: Choice,
    is_expanded: bool,
    position: Position,
}

#[derive(Debug, Clone)]
enum Position {
    Relative { x: f32, y: f32 },
    Absolute { x: f32, y: f32 },
}