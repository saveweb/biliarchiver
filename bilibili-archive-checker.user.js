// ==UserScript==
// @name         Bilibili Archive Checker
// @version      1.3
// @description  检查 BiliBili 视频是否已经存档到 Internet Archive。
// @author       yzqzss
// @match        https://www.bilibili.com/video/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function () {
    'use strict';

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function isVideo() {
        var url = window.location.href;
        var avRegex = /\/video\/av(\d+)/;
        var matches = url.match(avRegex);
        if (matches && matches.length > 1) {
            console.log("AV:", matches[1]);
            return true;
        }
        var bvRegex = /\/video\/(BV\w+)/;
        matches = url.match(bvRegex);
        if (matches && matches.length > 1) {
            console.log("BV:", matches[1]);
            return true;
        }
        return false;
    }

    function _av2bv(av) {
        return new Promise(resolve => {
          var api_url = "https://api.bilibili.com/x/web-interface/view?aid=" + av;
          console.log("Querying:", api_url);
          GM_xmlhttpRequest({
            method: "GET",
            url: api_url,
            onload: async function (response) {
              var data = JSON.parse(response.responseText);
              if (data.code === 0) {
                var bv = data.data.bvid;
                if (bv === undefined) {
                  console.log("Failed to convert AV to BV.");
                  console.log("data:", data);
                  resolve(null);
                } else {
                  console.log("av2bv succ:", bv);
                  resolve(bv);
                }
              } else {
                console.log("Failed to convert AV to BV.");
                console.log("data:", data);
                resolve(null);
              }
            }
          });
        });
      }
      
      async function av2bv(av) {
        try {
          const bv = await _av2bv(av);
          console.log("Converted BV:", bv);
          return bv;
        } catch (error) {
          console.error("An error occurred:", error);
        }
      }


    // 从 URL 获取当前视频的 BV 号
    async function getBVNumber() {
        var url = window.location.href;
        var avRegex = /\/video\/av(\d+)/;
        var bvRegex = /\/video\/(BV\w+)/;
        var bvMatches = url.match(bvRegex);
        if (bvMatches && bvMatches.length > 1) {
            console.log("BV:", bvMatches[1]);
            return bvMatches[1];
        }
        var avMatches = url.match(avRegex);
        if (avMatches && avMatches.length > 1) {
            console.log("AV:", avMatches[1]);
            var avNumber = avMatches[1];
            showPopup("正在查询 av" + avNumber + "对应的 BV 号", "yellow");
            var bvNumber = await av2bv(avNumber);
            console.log("Got BV from av2bv():", bvNumber);
            return bvNumber;
        }

        console.log("No BV number found.");
        return null;
    }

    function getPageNumber() {
        var url = window.location.href;
        var pageRegex = /p=(\d+)/;
        var matches = url.match(pageRegex);
        if (matches && matches.length > 1) {
            console.log("PageNumber:", matches[1]);
            return matches[1];
        }
        console.log("No PageNumber found, use 1.");
        return '1';
    }

    function humanReadableUpperPartMap(string, backward) {
        // 找到字符串中所有的 ASCII 大写字母，并返回一个能表示他们绝对位置的字符串。
        // 其中每个非相邻的大写字母之间用数字表示相隔的字符数。
        //
        // params: backward - 可以表示是正着看还是倒着看。
        //
        // NOTE: 在我们的用例中，我们 backward = true ，这样产生的 upperPart 就不太像 BV 号或者类似的编号，以免 upperPart 污染全文搜索。
        //
        // 例如：
        // backward = false
        //   BV1HP411D7Rj -> BV1HP3D1R （长得像 bvid ）
        // backward = true
        //   BV1HP411D7Rj -> 1R1D3PH1VB

        if (backward) {
            string = string.split('').reverse().join('');
        }

        let result = '';
        let steps = 0;
        let char_ = '';
        for (let i = 0; i < string.length; i++) {
            char_ = string[i];
            // console.log('char_:', char_);
            if (char_ >= 'A' && char_ <= 'Z') {
                if (steps === 0) {
                    result += char_;
                } else {
                    // steps to string
                    result += steps.toString() + char_;
                }
                steps = 0;
            } else {
                steps++;
            }
        }
        console.log("upperPart:", result);
        return result;
    }

    // 查 archive.org
    function queryInternetArchive(bvNumber, pageNumber) {
        var identifier = "BiliBili-" + bvNumber + "_p" + pageNumber + "-" + humanReadableUpperPartMap(bvNumber, true);
        var iaUrl = "https://archive.org/services/check_identifier.php?output=json&identifier=" + identifier;
        console.log("Querying:", iaUrl);
        showPopup("正在查询 IA (BV:" + bvNumber + ",P:"+pageNumber+")", "yellow")
        GM_xmlhttpRequest({
            method: "GET",
            url: iaUrl,
            onload: function (response) {
                var data = JSON.parse(response.responseText);
                if (data.code === "available") {
                    showPopup("未存档", "red");
                } else {
                    showPopup("本视频已存档", "green", "https://archive.org/details/" + identifier);
                }
            }
        });
    }

    // 创建悬浮窗
    function createPopup() {
        var popup = document.createElement("div");
        popup.id = "archive-popup";
        popup.style.position = "fixed";
        popup.style.top = "50%";
        popup.style.right = "10px";
        popup.style.transform = "translateY(-50%)";
        popup.style.padding = "10px";
        popup.style.backgroundColor = "#f0f0f0";
        popup.style.border = "1px solid #ccc";
        popup.style.borderRadius = "4px";
        popup.style.zIndex = "9999";
        popup.style.opacity = "0.9";

        var text = document.createElement("span");
        text.style.marginRight = "10px";
        text.style.color = "#333";
        text.textContent = "";

        var status = document.createElement("span");
        status.id = "item-status";

        var copyButton = document.createElement("button");
        copyButton.textContent = "Copy BV";
        copyButton.style.marginTop = "10px";
        copyButton.style.display = "block";
        copyButton.addEventListener("click", function () {
            copyBV();
        });

        popup.appendChild(text);
        popup.appendChild(status);
        popup.appendChild(copyButton);

        document.body.appendChild(popup);
    }

    // 显示悬浮窗
    function showPopup(message, color, href=null) {
        var popup = document.getElementById("archive-popup");
        if (!popup) {
            createPopup();
        }

        var status = document.getElementById("item-status");
        if (status) {
            status.textContent = message;
            if (href) {
                status.style.color = "blue";
                status.style.textDecoration = "underline";
                status.innerHTML = "<a href=\"" + href + "\" target=\"_blank\">" + message + "</a>";         
            }
        }
        popup = document.getElementById("archive-popup");
        popup.style.backgroundColor = color;
    }

    // 复制 BV 号
    async function copyBV() {
        var bvNumber = await getBVNumber();
        if (bvNumber) {
            navigator.clipboard.writeText(bvNumber)
                .then(function () {
                    alert("BV号已复制到剪贴板: " + bvNumber);
                })
                .catch(function (error) {
                    console.error("无法复制BV号:", error);
                });
        }
    }


    async function check() {
        if (!isVideo()) {
            console.log("Not a video page, skip.");
            return;
        }
        var bvNumber = await getBVNumber();
        var pageNumber = getPageNumber();
        if (bvNumber) {
            queryInternetArchive(bvNumber, pageNumber);
        }
        else {
            showPopup("无法获取 BV 号", "red");
        }
    }


    async function main() {
        var url = null;
        while (true) {
            url = window.location.href;
            console.log("url:", url);
            check();
            while (url === window.location.href) {
                // sleep 5s
                await sleep(5000);
            }
            showPopup("URL 变化...", "yellow");
        }
    }

    main();
})();
