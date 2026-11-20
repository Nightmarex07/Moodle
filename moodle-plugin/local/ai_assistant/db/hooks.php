<?php
defined('MOODLE_INTERNAL') || die();

$callbacks = [
    [
        'hook' => \core\hook\output\before_standard_head_html_generation::class,
        'callback' => \local_ai_assistant\hooks\output::class . '::before_standard_head_html_generation',
    ],
    [
        'hook' => \core\hook\output\before_footer_html_generation::class,
        'callback' => \local_ai_assistant\hooks\output::class . '::before_footer_html_generation',
    ],
];
