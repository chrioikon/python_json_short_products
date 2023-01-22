<?php
$target_dir = "./data/";
$target_file = $target_dir . $_FILES["itemUpload"]["name"];

// echo $target_file;
if (mime_content_type($_FILES["itemUpload"]["tmp_name"]) == "application/vnd.oasis.opendocument.spreadsheet"){
  if (move_uploaded_file($_FILES["itemUpload"]["tmp_name"], $target_file)) {
    header("Content-Type: text/plain");
    echo "File ".$_FILES["itemUpload"]["name"]." was uploaded.";
  } else {
    header("Content-Type: text/plain");
    echo "Sorry, there was an error uploading your file.";
  }
}else if (mime_content_type($_FILES["itemUpload"]["tmp_name"]) == "text/plain"){
  if (move_uploaded_file($_FILES["itemUpload"]["tmp_name"], $target_file)) {
    header("Content-Type: text/plain");
    echo "File ".$_FILES["itemUpload"]["name"]." was uploaded.";
  } else {
    header("Content-Type: text/plain");
    echo "Sorry, there was an error uploading your file.";
  }
}else{
  header("Content-Type: text/plain");
  echo "Sorry, there was an error uploading your file.";
}
?>