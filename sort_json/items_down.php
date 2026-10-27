<?php
require __DIR__ . '/common.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET' || !isset($_GET['action'])) {
    fail(400);
}
if ($_GET['action'] === 'display') {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(preg_grep('/\.csv$/', scandir(DATA_DIR)));
} elseif ($_GET['action'] === 'download') {
    send_download(data_path(isset($_GET['file']) ? $_GET['file'] : '', ['csv']));
} else {
    fail(400);
}
