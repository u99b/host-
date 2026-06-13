<?php
header('Content-Type: application/json');
$text = isset($_REQUEST['text']) ? $_REQUEST['text'] : 'Arab Team';

if (empty($text)) {
echo json_encode(['error' => 'Text parameter is required']);
exit;
}

$url = 'https://m.photofunia.com/ar/categories/all_effects/blood_writing?server=1';
$ch = curl_init($url);
$headers = [
'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
'Accept-Language: ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
'Origin: https://m.photofunia.com',
'Referer: https://m.photofunia.com/ar/effects/blood_writing',
'User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'
];
$cookieFile = tempnam(sys_get_temp_dir(), 'cookie');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, ['text' => $text]);
curl_setopt($ch, CURLOPT_COOKIEJAR, $cookieFile);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
$response = curl_exec($ch);
$info = curl_getinfo($ch);

curl_close($ch);
$resultUrl = $info['url'];
$ch = curl_init($resultUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_COOKIEFILE, $cookieFile);
$resultHtml = curl_exec($ch);
curl_close($ch);

if (file_exists($cookieFile)) {
unlink($cookieFile);
}

preg_match('/https:\/\/u\.photofunia\.com\/[^\s"\']+\.jpg/', $resultHtml, $matches);
if (isset($matches[0])) {
echo json_encode([
'By' => '@E_G_Y_0',
'status' => 'success',
'text' => $text,
'image_url' => $matches[0]
]);
} else {
preg_match('/src="(https:\/\/u\.photofunia\.com\/[^"]+)"/', $resultHtml, $matches);
if (isset($matches[1])) {
echo json_encode([
'By' => '@E_G_Y_0',
'status' => 'success',
'text' => $text,
'image_url' => $matches[1]
]);
} else {
echo json_encode([
'By' => '@E_G_Y_0',
'status' => 'error',
'message' => 'Could not find result image',
'debug_url' => $resultUrl
]);
}
}
?>