// ==UserScript==
// @name         Bilibili Archive Checker
// @version      1.4
// @description  检查 BiliBili 视频是否已经存档到 Internet Archive。
// @author       yzqzss
// @match        https://www.bilibili.com/video/*
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @grant        unsafeWindow
// ==/UserScript==

(function () {
    'use strict';

    const initialState = unsafeWindow.__INITIAL_STATE__;
    const BASEURL = ""; // 运行API的地址，不包括 /archive/ 部分

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

    // 从 URL 获取当前视频的 BV 号
    function getBVNumber() {
        return unsafeWindow.__INITIAL_STATE__?.bvid ?? initialState?.bvid ?? unsafeWindow.vd?.bvid;
    }

    function getPageNumber() {
        return unsafeWindow.__INITIAL_STATE__?.p ?? initialState?.p ?? unsafeWindow.vd?.embedPlayer?.p;
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
        showPopup("正在查询 IA (BV: " + bvNumber + ", P:" + pageNumber + ")", "#f3d9a6")
        GM_xmlhttpRequest({
            method: "GET",
            url: iaUrl,
            onload: function (response) {
                var data = JSON.parse(response.responseText);
                if (data.code === "available") {
                    showPopup("未存档", "#fac7c7");
                } else {
                    showPopup("本视频已存档", "#bdf8bd", "https://archive.org/details/" + identifier);
                }
            }
        });
    }

    // 创建悬浮窗
    function createPopup() {
        var popup = document.createElement("div");
        popup.id = "archive-popup";
        popup.style.position = "fixed";
        popup.style.userSelect = "none"; // 否则选中会出现横向滚动条
        popup.style.top = "50%";
        popup.style.right = "10px";
        popup.style.transform = "translateY(-50%)";
        popup.style.padding = "10px";
        popup.style.backgroundColor = "#f0f0f0";
        popup.style.border = "1px solid #ccc";
        popup.style.borderRadius = "4px";
        popup.style.zIndex = "9999";
        popup.style.opacity = "0.9";
        popup.style.transition = "background-color 0.25s";

        var text = document.createElement("span");
        text.style.marginRight = "10px";
        text.style.color = "#333";
        text.textContent = "";

        var status = document.createElement("span");
        status.id = "item-status";

        var copyButton = document.createElement("button");
        copyButton.textContent = "Copy BV";
        copyButton.style.marginTop = "10px";
        copyButton.style.padding = "5px";
        copyButton.style.margin = "auto";
        copyButton.style.display = "block";
        copyButton.addEventListener("click", function () {
            copyBV();
        });

        var archiveButton = document.createElement("button");
        archiveButton.textContent = "Archive Video";
        archiveButton.style.marginTop = "10px";
        archiveButton.style.padding = "5px";
        archiveButton.style.margin = "auto";
        archiveButton.style.display = "block"; // initially hidden
        archiveButton.addEventListener("click", function () {
            archiveVideo();
        });

        popup.appendChild(text);
        popup.appendChild(status);
        popup.appendChild(copyButton);
        popup.appendChild(archiveButton);

        document.body.appendChild(popup);
    }

    // 显示悬浮窗
    function showPopup(message, color, href = null) {
        var popup = document.getElementById("archive-popup");
        if (!popup) {
            createPopup();
        }

        var status = document.getElementById("item-status");
        if (status) {
            status.textContent = message;
            if (href) {
                status.style.color = "#b6e9fe";
                status.style.textDecoration = "underline";
                status.innerHTML = "<a href=\"" + href + "\" target=\"_blank\">" + message + "</a>";
            }
        }
        popup = document.getElementById("archive-popup");
        popup.style.backgroundColor = color;
    }

    // 复制 BV 号
    async function copyBV() {
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


    async function check() {
        if (!isVideo()) {
            console.log("Not a video page, skip.");
            return;
        }
        var bvNumber = getBVNumber();
        var pageNumber = getPageNumber();
        if (bvNumber) {
            queryInternetArchive(bvNumber, pageNumber);
        }
        else {
            showPopup("无法获取 BV 号", "#f3d9a6");
        }
    }

    async function archiveVideo() {
        var bvNumber = getBVNumber();
        var url = `${BASEURL}/archive/${bvNumber}`;
        console.log("Archive URL:", url);
        showPopup("正在发送存档请求", "#f3d9a6");
        GM_xmlhttpRequest({
            method: "PUT",
            url: url,
            onload: function (response) {
                if (response.status === 200) {
                    showPopup("存档请求已发送", "#bdf8bd");
                } else {
                    showPopup("存档请求失败", "#fac7c7");
                }
            }
        });
    }


    async function main() {
        var url = null;
        while (true) {
            url = window.location.href.split('&')[0];
            console.log("url:", url);
            check();
            while (url === window.location.href.split('&')[0]) {
                await sleep(5000);
            }
            showPopup("URL 变化...", "#b6e9fe");
        }
    }

    document.addEventListener("DOMContentLoaded", main);
})();
