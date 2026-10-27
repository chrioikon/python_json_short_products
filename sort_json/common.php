<?php
// Helpers shared by the PHP endpoints.

const DATA_DIR = './data/';

// Path of $name inside the data folder, or false if $name is not a plain file
// name with one of the allowed extensions. This blocks "../" path traversal.
function data_path($name, array $extensions)
{
    if (!is_string($name) || $name === '' || $name[0] === '.' || strpbrk($name, "/\\\0") !== false) {
        return false;
    }
    if (!in_array(strtolower(pathinfo($name, PATHINFO_EXTENSION)), $extensions, true)) {
        return false;
    }
    return DATA_DIR . $name;
}

// Quote a string as a single shell argument. Unlike escapeshellarg() it keeps
// non-ASCII (e.g. Hebrew) characters whatever the locale is.
function shell_quote($value)
{
    return "'" . str_replace("'", "'\\''", $value) . "'";
}

function fail($status, $message = '')
{
    http_response_code($status);
    header('Content-Type: text/plain; charset=utf-8');
    echo $message;
    exit;
}

function send_download($path)
{
    if ($path === false || !is_file($path)) {
        fail(404, 'File not found.');
    }
    header('Content-Description: File Transfer');
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="' . basename($path) . '"');
    header('Expires: 0');
    header('Cache-Control: must-revalidate');
    header('Pragma: public');
    header('Content-Length: ' . filesize($path));
    readfile($path);
    exit;
}
