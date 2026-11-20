<?php
defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_ai_assistant', get_string('pluginname', 'local_ai_assistant'));
    $ADMIN->add('localplugins', $settings);

    $settings->add(new admin_setting_configcheckbox(
        'local_ai_assistant/enabled',
        get_string('enabled', 'local_ai_assistant'),
        get_string('enabled_desc', 'local_ai_assistant'),
        1
    ));

    $settings->add(new admin_setting_configtext(
        'local_ai_assistant/backendurl',
        get_string('backendurl', 'local_ai_assistant'),
        get_string('backendurl_desc', 'local_ai_assistant'),
        'http://localhost:8000',
        PARAM_TEXT
    ));

    $settings->add(new admin_setting_configpasswordunmask(
        'local_ai_assistant/apikey',
        get_string('apikey', 'local_ai_assistant'),
        get_string('apikey_desc', 'local_ai_assistant'),
        ''
    ));
}
