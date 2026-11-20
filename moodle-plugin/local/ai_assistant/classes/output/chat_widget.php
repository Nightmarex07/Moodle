<?php
namespace local_ai_assistant\output;

defined('MOODLE_INTERNAL') || die();

use renderable;
use templatable;
use renderer_base;
use stdClass;

class chat_widget implements renderable, templatable {
    public function __construct(
        private int $courseid,
        private string $backendurl,
        private string $apikey,
        private int $userid = 0,
        private string $userrole = 'student'
    ) {}

    public function export_for_template(renderer_base $output): stdClass {
        global $CFG;
        $data = new stdClass();
        $data->courseid = $this->courseid;
        $data->proxyurl = (new \moodle_url('/local/ai_assistant/proxy.php'))->out(false);
        $data->sesskey = sesskey();
        // Keep backendurl/apikey empty in template for security; proxy handles server-side.
        $data->backendurl = '';
        $data->apikey = '';
        $data->userid = $this->userid;
        $data->userrole = $this->userrole;
        $data->title = get_string('pluginname', 'local_ai_assistant');
        $data->subtitle = get_string('subtitle', 'local_ai_assistant');
        $data->openchat = get_string('openchat', 'local_ai_assistant');
        $data->placeholder = get_string('placeholder', 'local_ai_assistant');
        $data->send = get_string('send', 'local_ai_assistant');
        $data->disclaimer = get_string('disclaimer', 'local_ai_assistant');
        return $data;
    }
}
