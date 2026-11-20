<?php
namespace local_ai_assistant\hooks;

defined('MOODLE_INTERNAL') || die();

class output {
    private static function should_inject(): bool {
        global $PAGE, $COURSE;

        if (empty(get_config('local_ai_assistant', 'enabled'))) {
            return false;
        }
        if (!$PAGE->context || $PAGE->context->contextlevel !== CONTEXT_COURSE) {
            return false;
        }
        $courseid = isset($COURSE->id) ? (int)$COURSE->id : 0;
        return $courseid > 1;
    }

    public static function before_standard_head_html_generation(\core\hook\output\before_standard_head_html_generation $hook): void {
        global $PAGE;
        if (!self::should_inject()) {
            return;
        }
        $PAGE->requires->css('/local/ai_assistant/styles.css');
    }

    public static function before_footer_html_generation(\core\hook\output\before_footer_html_generation $hook): void {
        global $PAGE, $COURSE, $USER;

        if (!self::should_inject()) {
            return;
        }

        $courseid = isset($COURSE->id) ? (int)$COURSE->id : 0;
        $backendurl = (string)get_config('local_ai_assistant', 'backendurl');
        $apikey = (string)get_config('local_ai_assistant', 'apikey');
        $userid = isset($USER->id) ? (int)$USER->id : 0;
        $role = has_capability('moodle/course:manageactivities', $PAGE->context) ? 'teacher' : 'student';

        $renderable = new \local_ai_assistant\output\chat_widget($courseid, $backendurl, $apikey, $userid, $role);
        $renderer = $PAGE->get_renderer('local_ai_assistant');
        $hook->add_html($renderer->render($renderable));

        $PAGE->requires->js_call_amd('local_ai_assistant/chat_widget', 'init');
    }
}
