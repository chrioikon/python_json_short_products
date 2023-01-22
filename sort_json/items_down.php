<?php
if ($_SERVER['REQUEST_METHOD'] == 'GET'){
    if ($_GET["action"] == 'display'){
        header("Content-Type: application/json; charset=utf-8");
        print_r(json_encode(preg_grep("/\.csv$/",scandir("./data"))));
    }else if ($_GET["action"] == 'download'){
        if (isset($_GET["file"])){
            
            header('Content-Description: File Transfer');
            header('Content-Type: application/octet-stream');
            header('Content-Disposition: attachment; filename="'.basename($_GET["file"]).'"');
            header('Expires: 0');
            header('Cache-Control: must-revalidate');
            header('Pragma: public');
            header('Content-Length: ' . filesize("./data/".$_GET["file"]));
            readfile("./data/".$_GET["file"]);
            exit;
        }
    }
}
