// ==UserScript==
// @name         Bilibili Archive Checker
// @version      1.1
// @description  多 p 视频只检查 p1 是否存在。
// @author       yzqzss
// @match        https://www.bilibili.com/video/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function () {
    'use strict';

    // 从 URL 获取当前视频的 BV 号
    function getBVNumber() {
        var url = window.location.href;
        var bvRegex = /\/video\/(BV\w+)/;
        var matches = url.match(bvRegex);
        if (matches && matches.length > 1) {
            console.log("BV:", matches[1]);
            return matches[1];
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
        var iaUrl = "https://archive.org/services/check_identifier.php?output=json&identifier=BiliBili-" + bvNumber + "_p" + pageNumber + "-" + humanReadableUpperPartMap(bvNumber, true);
        console.log("Querying:", iaUrl);
        GM_xmlhttpRequest({
            method: "GET",
            url: iaUrl,
            onload: function (response) {
                var data = JSON.parse(response.responseText);
                if (data.code === "available") {
                    showPopup("此视频没有存档过", "red");
                } else {
                    showPopup("本视频已存档", "green");
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
        text.textContent = "Item Status: ";

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
    function showPopup(message, color) {
        var popup = document.getElementById("archive-popup");
        if (!popup) {
            createPopup();
        }

        var status = document.getElementById("item-status");
        if (status) {
            status.textContent = message;
        }
        popup = document.getElementById("archive-popup");
        popup.style.backgroundColor = color;
    }

    // 复制 BV 号
    function copyBV() {
        var bvNumber = getBVNumber();
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



    function main() {
        var bvNumber = getBVNumber();
        var pageNumber = getPageNumber();
        if (bvNumber) {
            queryInternetArchive(bvNumber, pageNumber);
        }
    }


    main();
})();
