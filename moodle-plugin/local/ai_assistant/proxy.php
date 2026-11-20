<?php
require_once(__DIR__ . '/../../config.php');

require_login();
$action = required_param('action', PARAM_ALPHA);
$courseid = required_param('courseid', PARAM_INT);
$sesskey = required_param('sesskey', PARAM_RAW);

if (!confirm_sesskey($sesskey)) {
    http_response_code(403);
    echo json_encode(['error' => 'Invalid sesskey']);
    exit;
}

$context = context_course::instance($courseid);
require_capability('moodle/course:view', $context);

$backendurl = rtrim(trim((string)get_config('local_ai_assistant', 'backendurl')), '/');
$apikey = trim((string)get_config('local_ai_assistant', 'apikey'));
if ($backendurl === '' || $apikey === '') {
    http_response_code(500);
    echo json_encode(['error' => 'Backend not configured']);
    exit;
}

$userid = $USER->id;
$role = has_capability('moodle/course:manageactivities', $context) ? 'teacher' : 'student';

if ($action === 'history') {
    $url = $backendurl . '/api/v1/history?course_id=' . urlencode((string)$courseid) . '&user_id=' . urlencode((string)$userid);
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['X-API-Key: ' . $apikey]);
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE) ?: 500;
    $err = curl_error($ch);
    $errno = curl_errno($ch);
    curl_close($ch);
    if ($resp === false || $errno) {
        @file_put_contents('/tmp/ai_proxy_debug.log', date('c') . " history fail errno=$errno err=$err code=$code\n", FILE_APPEND);
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['error' => 'Proxy request failed', 'detail' => $err, 'errno' => $errno]);
        exit;
    }
    @file_put_contents('/tmp/ai_proxy_debug.log', date('c') . " history ok code=$code\n", FILE_APPEND);
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo $resp !== '' ? $resp : json_encode(['error' => 'Empty response']);
    exit;
}

if ($action === 'chat') {
    $raw = file_get_contents('php://input');
    $payload = json_decode($raw, true);
    if (!is_array($payload)) {
        $payload = [];
    }
    $payload['course_id'] = $courseid;
    $payload['user_id'] = (string)$userid;
    $payload['user_role'] = $role;
    $payload['stream'] = true;

    $url = $backendurl . '/api/v1/chat';

    // Disable Moodle/PHP output buffering for SSE streaming.
    @ini_set('output_buffering', 'off');
    @ini_set('zlib.output_compression', '0');
    while (ob_get_level() > 0) {
        @ob_end_clean();
    }

    header('Content-Type: text/event-stream; charset=utf-8');
    header('Cache-Control: no-cache, no-transform');
    header('X-Accel-Buffering: no');
    header('Connection: keep-alive');
    header('Content-Encoding: none');

    // Send padding to encourage flush through proxies/buffers.
    echo ": stream-start\n\n";
    @flush();

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'X-API-Key: ' . $apikey,
        'Accept: text/event-stream',
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 0);
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
        echo $data;
        if (ob_get_level() > 0) {
            @ob_flush();
        }
        @flush();
        return strlen($data);
    });

    $ok = curl_exec($ch);
    $httpcode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if ($ok === false || ($httpcode >= 400 && $httpcode !== 0)) {
        $err = curl_error($ch);
        $errno = curl_errno($ch);
        $msg = $err ? ('Proxy error: ' . $err) : ('Backend HTTP error: ' . $httpcode);
        @file_put_contents('/tmp/ai_proxy_debug.log', date('c') . " chat fail errno=$errno http=$httpcode err=$err\n", FILE_APPEND);
        echo "event: error\n";
        echo 'data: ' . json_encode([
            'message' => $msg,
            'errno' => $errno,
            'http_code' => $httpcode,
        ], JSON_UNESCAPED_UNICODE) . "\n\n";
        @flush();
    } else {
        @file_put_contents('/tmp/ai_proxy_debug.log', date('c') . " chat ok http=$httpcode\n", FILE_APPEND);
    }
    curl_close($ch);
    exit;
}

http_response_code(400);
echo json_encode(['error' => 'Unknown action']);
