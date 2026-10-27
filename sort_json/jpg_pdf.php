<?php
require __DIR__ . '/common.php';

// Menu pages to capture, relative to this script, and the image each is saved to.
const MENU_PAGES = [
    '../menu/index.php' => 'index.jpg',
    '../menu/index_flowers.php' => 'index_flowers.jpg',
    '../menu/index_others.php' => 'index_others.jpg',
];

// Turn the URL of this script into the URL of $path, a path relative to it.
function breakToUrl($url, $path)
{
    $regex = 'jpg_pdf\.php?.*';
    for ($i = 0; $i < preg_match_all('/\.\.\//', $path); $i++) {
        $regex = "[\w+-._~]+\/" . $regex;
    }
    return preg_replace("/" . $regex . "/", '', $url) . preg_replace('/(\.\.\/)|(\.\/)/', '', $path);
}

if ($_SERVER['REQUEST_METHOD'] !== 'GET' || !isset($_GET['option'])) {
    fail(400);
}

if ($_GET['option'] === 'exec') {
    $scheme = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on') ? 'https://' : 'http://';
    $url = $scheme . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
    foreach (MENU_PAGES as $page => $image) {
        echo shell_exec('./take_screenshot.py -u ' . shell_quote(breakToUrl($url, $page)) .
            ' -o ' . shell_quote(DATA_DIR . $image));
    }
} elseif ($_GET['option'] === 'download') {
    send_download(data_path(isset($_GET['file']) ? $_GET['file'] : '', ['jpg', 'pdf']));
} else {
    fail(400);
}
