<?php
// 
//حقوق @ROIUCX
//حقوق @ROIUCX

$token   = "TOKEN";  // ضع توكن حب 
$api_url = "https://devil.xo.je/v/ai/claude.php";  //   
$channel = "@ROIUCX";      

$update = json_decode(file_get_contents("php://input"), true);

//حقوق @ROIUCX
//حقوق @ROIUCX
if (isset($update['message'])) {
    $message = $update['message'];
    $chat_id = $message['chat']['id'];
    $text = trim($message['text'] ?? '');
    
    //حقوق @ROIUCX
//حقوق @ROIUCX
    if ($text == '/start') {
        $welcome = " *مرحباً بك في بوت المحادثة بالذكاء الاصطناعي!*\n\n";
        $welcome .= "أنا بوت يعمل بنموذج *Claude 3.7 Sonnet*\n\n";
        $welcome .= " *الطريقة:*\n";
        $welcome .= "فقط أرسل سؤالك أو رسالتك وسأجيبك فوراً.\n\n";
        $welcome .= " *قناة البوت:* $channel";
        
        //حقوق @ROIUCX
//حقوق @ROIUCX
        $keyboard = json_encode([
            'inline_keyboard' => [
                [['text' => ' قناة البوت', 'url' => 'https://t.me/ROIUCX']]
            ]
        ]);
        
        sendMessage($token, $chat_id, $welcome, $keyboard);
        exit;
    }
    
   //حقوق @ROIUCX
//حقوق @ROIUCX
    if (!empty($text) && !str_starts_with($text, '/')) {
     //حقوق @ROIUCX
//حقوق @ROIUCX
        file_get_contents("https://api.telegram.org/bot{$token}/sendChatAction?chat_id={$chat_id}&action=typing");
        
     //حقوق @ROIUCX
//حقوق @ROIUCX
        $response = callClaudeAPI($api_url, $text);
        
        if ($response && isset($response['success']) && $response['success'] == true) {
            $reply = $response['response'] ?? 'عذراً، لم أستطع معالجة طلبك.';
            sendMessage($token, $chat_id, $reply);
        } elseif ($response && isset($response['response'])) {
            sendMessage($token, $chat_id, $response['response']);
        } elseif ($response && isset($response['error'])) {
            sendMessage($token, $chat_id, " *خطأ:*\n" . $response['error']);
        } else {
            sendMessage($token, $chat_id, " عذراً، حدث خطأ في الاتصال. حاول مرة أخرى.");
        }
    }
}

//حقوق @ROIUCX
//حقوق @ROIUCX

function callClaudeAPI($api_url, $message) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_url . "?message=" . urlencode($message));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode != 200 || !$response) {
        return null;
    }
    
    return json_decode($response, true);
}

function sendMessage($token, $chat_id, $text, $keyboard = null) {
    $url = "https://api.telegram.org/bot{$token}/sendMessage";
    $postData = [
        'chat_id' => $chat_id,
        'text' => $text,
        'parse_mode' => 'Markdown'
    ];
    if ($keyboard) {
        $postData['reply_markup'] = $keyboard;
    }
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_exec($ch);
    curl_close($ch);
}
?>