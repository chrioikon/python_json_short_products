<?php
require __DIR__ . '/common.php';

// Allowed MIME types for each uploadable extension.
const UPLOAD_TYPES = [
    'ods' => ['application/vnd.oasis.opendocument.spreadsheet'],
    'csv' => ['text/plain', 'text/csv', 'application/csv'],
];

if (!isset($_FILES['itemUpload']) || $_FILES['itemUpload']['error'] !== UPLOAD_ERR_OK) {
    fail(400, 'Sorry, there was an error uploading your file.');
}
$upload = $_FILES['itemUpload'];
$target_file = data_path($upload['name'], array_keys(UPLOAD_TYPES));
if ($target_file === false) {
    fail(400, 'Sorry, only .ods and .csv files can be uploaded.');
}

$extension = strtolower(pathinfo($upload['name'], PATHINFO_EXTENSION));
if (!in_array(mime_content_type($upload['tmp_name']), UPLOAD_TYPES[$extension], true)) {
    fail(400, 'Sorry, the file content does not match its extension.');
}
if (!move_uploaded_file($upload['tmp_name'], $target_file)) {
    fail(500, 'Sorry, there was an error uploading your file.');
}

header('Content-Type: text/plain; charset=utf-8');
echo 'File ' . $upload['name'] . ' was uploaded.';
