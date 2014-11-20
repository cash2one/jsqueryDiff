var page = require('webpage').create(),
    system = require('system'),
    fs = require('fs');

if(system.args.length !== 2) {
    console.log('Usage: surf_webpage.js <some file>');
    phantom.exit();
}

//获取输入的文件地址
var file = system.args[1];

var urlFile = fs.open(file, 'r');
/*
page.open('http://www.kuailebz.com/tuan/index.php?page=65', function(status) {
    if (status != 'success') {
        console.log('Unable to access networ');
        phantom.exit();
    }else {
        console.log('success googd');
    }
    phantom.exit();
});
*/
function   sleep(n) 
    { 
        var   start=new   Date().getTime(); 
        while(true)   if(new   Date().getTime()-start> n)   break; 
    } 

surfWebpage();
function surfWebpage() {
    if (urlFile.atEnd()) {
        phantom.exit();
    } else {
        var webPage = urlFile.readLine();
        page.open(webPage, function(status) {
            if (status !== 'success') {
                console.log('Unable to access the web page:' + webPage);
            } else {
                sleep(100);
                console.log('web page success:' + webPage);
                surfWebpage();
            }   
        });    
    } 
}

