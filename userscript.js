// ==UserScript==
// @name         Bilibili Archive Checker
// @version      1.0
// @description  多 p 视频只检查 p1 是否存在。
// @author       yzqzss
// @match        https://www.bilibili.com/video/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function() {
    'use strict';

    // 从 URL 获取当前视频的 BV 号
    function getBVNumber() {
        var url = window.location.href;
        var bvRegex = /\/video\/(BV\w+)/;
        var matches = url.match(bvRegex);
        if (matches && matches.length > 1) {
            return matches[1];
        }
        return null;
    }

    // 查 archive.org
    function queryInternetArchive(bvNumber) {
        var iaUrl = "https://archive.org/services/check_identifier.php?output=json&identifier=BiliBili-" + bvNumber + "_p1";
        GM_xmlhttpRequest({
            method: "GET",
            url: iaUrl,
            onload: function(response) {
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
        copyButton.addEventListener("click", function() {
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
                .then(function() {
                    alert("BV号已复制到剪贴板: " + bvNumber);
                })
                .catch(function(error) {
                    console.error("无法复制BV号:", error);
                });
        }
    }



    function main() {
        var bvNumber = getBVNumber();
        if (bvNumber) {
            queryInternetArchive(bvNumber);
        }
    }


    main();
})();
