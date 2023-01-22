<?php

function breakToUrl($url,$path){
    $regex = 'jpg_pdf\.php?.*';
    for ($i=0;$i<preg_match_all('/\.\.\//',$path);$i++){
        $regex = "[\w+-._~]+\/" . $regex;
    }
    return preg_replace("/".$regex."/",'',$url).preg_replace('/(\.\.\/)|(\.\/)/','',$path);
}


if ($_SERVER['REQUEST_METHOD']=='GET'){
    if ($_GET['option'] =="exec"){
    $output ="";
    //    echo $output ="executing jpg_pdf";
        if(isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on')   
            $url = "https://";   
        else  
            $url = "http://";   
        
        $url.= $_SERVER['HTTP_HOST'];   
        
        
        $url.= $_SERVER['REQUEST_URI'];    
            
        echo $output = shell_exec("./take_screenshot.py -u ".breakToUrl($url,'../menu/index.php')." -o ./data/index.jpg");
        echo $output = shell_exec("./take_screenshot.py -u ".breakToUrl($url,'../menu/index_flowers.php')." -o ./data/index_flowers.jpg");
        echo $output = shell_exec("./take_screenshot.py -u ".breakToUrl($url,'../menu/index_others.php')." -o ./data/index_others.jpg");
    }else if ($_GET['option'] == "download"){
 //       echo $output ="downloading jpg_pdf";
        if (isset($_GET["file"])){
            if (file_exists("./data/".$_GET["file"])){
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

}

?>