<?php
namespace local_ai_assistant\output;

defined('MOODLE_INTERNAL') || die();

use plugin_renderer_base;

class renderer extends plugin_renderer_base {
    public function render_chat_widget(chat_widget $widget): string {
        $data = $widget->export_for_template($this);
        return $this->render_from_template('local_ai_assistant/chat_widget', $data);
    }
}
