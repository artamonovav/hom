/*
 *	update 2025.05.14 改善施策
 */
const MANUAL_NAME = "FREED";
const MANUAL_YEAR = "2025";
const MANUAL_PATH = "/ownersmanual/webom/jpn/freed/2025/";
const KEYWORDS = "$KEYWORDS$";
const DESCRIPTION = "$DESCRIPTION$";
const HAS_NAVI = false;
const HAS_BANNER_MOV = true;

const _DEVICE_PC = 0;
const _DEVICE_TAB = 1;
const _DEVICE_SP = 2;

const SEARCH_FILTER_WORD = "FREED\t2025"; //2025.05.14 mars search filter
const COOKIE_AGREEMENT = "ownersmanualwebomjpn"; //2025.05.14

function setbc() {
  $("body").css({opacity: 1});
}

////////////////////////////////////////

/**
 * 	lastupdate: 2022.06.06 16:04
 *  lastupdate: 2023.03.14 15:50
 */

window.addEventListener("DOMContentLoaded", function () {
  setStyle();
  setHead();
  setLayout();
  setPageClass();
  setGlobalNav();

  //車体
  loadSide({
    json: getPath("../language/ja_JP/main/json/contentsDB.json"),
    $target: $(".nav-side"),
    className: "root",
    detailsDir: "../details/",
    callback: function () {
      // --- dOM廃止bannerを表示 20251123 SHimizu
      // --- NAV搭載車のみバナー表示できる仕様を全車対応に変更
      // --- 全車対応：（HAS_NAVI判定より前） にcallbackでbanner追加

      // --- バナー挿入を先に実行（HAS_NAVI判定より前） ---
      (function insertBannerToMenuEnd() {
        // すでに挿入済みなら何もしない（重複防止）
        if ($(".listtitle.of-banner01").length > 0) return;

        // サイドメニュー（ul.root）が生成されている前提
        const $root = $("ul.root");
        if ($root.length === 0) return;

        // バナー画像パス（index と下層で切替）
        const banner_path = is_index() ? "./asset/images/dOM.png" : "../asset/images/dOM.png";

        // お知らせページへの相対パス（MANUAL_PATH 前提）
        const announceHref = is_index() ? "../../../../HondaMotor/auto/announce.html" : "../../../../../HondaMotor/auto/announce.html";

        // バナー要素を生成
        const $li_banner_01 = $("<li>").append(
          $("<p>")
          .addClass("listtitle of-banner01")
          .append(
            $("<a>")
            .append($("<img>").attr({src: banner_path}))
            .css({display: "block"})
            .attr({href: announceHref, target: "_blank"})
          )
        );

        // メニューの末尾に追加
        $root.append($li_banner_01);
      })();

      // --- バナー挿入ここまで ---

      if (!HAS_NAVI) {
        if (is_toclist()) {
          initTocList($(".nav-side > .root").clone());
        }
        return;
      }

      //add menu
      let $li_connect;
      let $navititle_inserted = false;
      $("ul.root > li > .listtitle").each(function (listtiel_index) {
        //if( $(this).html() === "運転"){
        if ($navititle_inserted == false && listtiel_index == $("ul.root > li > .listtitle").length - 2) {
          $li_connect = $("<li>").append($("<div>").addClass("listtitle of-navi").html("$NAVI_TITLE$"));
          $(this).closest("li").after($li_connect);
          $navititle_inserted = true;
        }

        // --- dOM廃止banner表示で不要になった、
        // --- Q&Aページ依存とyoutubeをコメントアウト20251113 SHimizu
        // if (HAS_BANNER_MOV) {
        //   if ($(this).html() === "Q&amp;A") {
        //     let banner_path = is_index() ? "./asset/images/dOM.png" : "../asset/images/dOM.png";

        //     const $li_banner_01 = $("<li>").append(
        //       $("<div>")
        //       .addClass("listtitle of-banner01")
        //       .append(
        //         $("<a>")
        //         .append($("<img>").attr({src: banner_path}))
        //         .css({display: "block"})
        //         .attr({href: "https://www.youtube.com/watch?v=rZ6CKPl2rX4", target: "_blank"})
        //       )
        //     );
        //     $(this).closest("li").after($li_banner_01);
        //   }
        // }
      });

      //ナビ
      loadSide({
        json: getPath("../language/ja_JP/navi/json/contentsDB.json"),
        $target: $li_connect,
        className: "-L1",
        detailsDir: "../detailsnavi/",
        callback: function () {
          //setHead();
          setStyle();
          $("body").css({opacity: 1});
          //$('.slider').css({'opacity':1});
          $(window).trigger("resize");

          if (is_toclist()) {
            initTocList($(".nav-side > .root").clone());
          }
        },
      });
    },
  });

  setContainerMore();

  // 新しい関数を呼び出し、scrollxクラスを追加 240423saiki
  addScrollxToTableWrap();

  //2024/04/30 saiki
  addClassForDoubleDigit();

  // 2024/06/17更新 saiki
  var links = document.querySelectorAll("a[href]");
  links.forEach(function (link) {
    var href = link.getAttribute("href");
    // リンクが https:// で始まり、かつ https://www.honda.co.jp で始まらない場合、または shopsearch.honda.co.jp/auto/area/ に一致する場合
    if ((href.startsWith("https://") && !href.startsWith("https://www.honda.co.jp")) || /(\.\.\/)+HondaMotor\/auto\//.test(href) || href.includes("shopsearch.honda.co.jp/auto/area/")) {
      link.setAttribute("target", "_blank");
    } else {
      // それ以外のリンクは同じタブで開く
      link.removeAttribute("target");
    }
  });

  // footer 内のすべてのリンクを新しいタブで開くように設定
  var footerLinks = document.querySelectorAll("#footer a[href]");
  footerLinks.forEach(function (link) {
    link.setAttribute("target", "_blank");
  });

  setPageIndex();
  changePosErrorList();
  clearEmptyTag();
  changeNavImgPath();
  setMarsSearch();
  checkHref();
  setTitle();
  setMeta();
});

window.addEventListener("load", function () {
  agreement();

  showPopBookmark();
  scrollByHash();

  // 2025.05.14 mars search filter
  setTimeout(function () {
    setSearchFilter();
  }, 500);
  $("body").css({opacity: 1});
  setSlick();
  setTimeout(function () {
    $("body").css({opacity: 1});
  }, 200);
});

///////////////////////////////////////////////////////////

function setHead() {
  //const favicon = '<link rel="shortcut icon" href="//www.honda.co.jp' + MANUAL_PATH + 'favicon.ico">';
  const appleiocn = '<link rel="apple-touch-icon" href="//www.honda.co.jp' + MANUAL_PATH + 'webclip.png">';
  const appleiocn_relative = '<link rel="apple-touch-icon" href="' + getRoot("") + 'webclip.png">';

  //$('head link:last').after(favicon);
  $("head link:last").after(appleiocn);
  $("head link:last").after(appleiocn_relative);

  if (HAS_NAVI && is_navi()) {
    $("head link:last").after('<link rel="stylesheet" type="text/css" href="../css/navi.css">');
    $("head link:last").after('<script src="../javascript/navi.js"></script>');
  }
}

function setTitle() {
  let myTitle = "";
  const bread = " | " + MANUAL_NAME + " " + MANUAL_YEAR + " | Honda";
  if (!document.title) {
    if (is_visual()) {
      myTitle = "画像から探す" + bread;
    } else if (is_toclist()) {
      myTitle = "一覧目次" + bread;
    } else if (is_index()) {
      myTitle = MANUAL_NAME + " " + MANUAL_YEAR + " | Honda";
    } else if (is_navi()) {
      myTitle = $(".title").eq(0).text() + bread;
    } else if (location.pathname.indexOf("lamp.html") >= 0) {
      myTitle = "警告灯/表示灯一覧" + bread;
    } else {
      myTitle = $(".title").eq(0).text() + bread;
    }
    setTimeout(function () {
      $("title").html(myTitle);
    }, 300);
  }
}

function setMeta() {
  let myMeta = "";

  if ($('meta[name="description"]').attr("content") == "") {
    /*
	    	if( is_visual() ){
	    		myMeta = MANUAL_NAME + 'の取扱説明ページです。' + MANUAL_NAME +'の取扱い方法をご確認いただけます。';
	    	}else if( is_toclist() ){
	    		myMeta = MANUAL_NAME + 'の取扱説明ページです。' + MANUAL_NAME +'の取扱い方法「一覧目次」をご確認いただけます。';
	    	}else if( is_index() ){
	    		//myMeta = MANUAL_NAME;
	    	}else if( is_navi() ){
	    		myMeta = MANUAL_NAME + 'の取扱説明ページです。' + MANUAL_NAME +'の取扱い方法「'+ $('.title').eq(0).text() +'」をご確認いただけます。';
	    	}else if( location.pathname.indexOf('lamp.html') >= 0 ){
	    		myMeta = MANUAL_NAME + 'の取扱説明ページです。' + MANUAL_NAME +'の取扱い方法「警告灯一覧」をご確認いただけます。';
	    	}else{
	    		myMeta = MANUAL_NAME + 'の取扱説明ページです。' + MANUAL_NAME +'の取扱い方法「'+ $('.title').eq(0).text() +'」をご確認いただけます。';
	    	}
	    	*/
    myMeta = $DESCRIPTION$;
    $('meta[name="description"]').attr({content: myMeta});
  }
  let myKeywords = "$KEYWORDS$";
  $('meta[name="keywords"]').attr({content: myKeywords});
}

function setPageClass() {
  if (is_visual()) {
    $("body").addClass("page-visual");
  } else if (is_toclist()) {
    $("body").addClass("page-toclist");
  } else if (is_index()) {
    $("body").addClass("page-index");
  } else if (is_navi()) {
    $("body").addClass("page-navi is-navi");
  } else if (location.pathname.indexOf("lamp.html") >= 0) {
    $("body").addClass("page-lamp");
  }
}

function changeNavImgPath() {
  if (is_navi()) {
    //console.log($('.main img') )
    $(".main img").each(function () {
      let path = $(this).attr("src");
      $(this).attr({src: path.replace("img", "imgnavi"), title: path.replace("img", "imgnavi")});
    });
  }
}

function setStyle() {
  //delete inline style
  $("*").not("tbody,tr,table,td,th").not("table div").removeAttr("style");

  changeProperty($("table"));
  changeProperty($("tbody"));
  changeProperty($("tr"));
  changeProperty($("td"));
  changeProperty($("th"));

  if ($(".table_set.callout").length > 0) {
    $(".table_set.callout > li").each(function () {
      if ($(this).find("span > img").length == 0) {
        $(this).addClass("noncounter");
      }
    });
  }

  if ($("span.frame").length > 0) {
    $("span.frame").each(function () {
      let myHtml = $(this).html();
      //&nbsp;+&nbsp;
      if (myHtml === "&nbsp;+&nbsp;" || myHtml === "&nbsp;-&nbsp;") {
        $(this).addClass("round");
      }
    });
  }

  //delete page style
  $("style").remove();

  $("body").css({opacity: 1});

  function changeProperty($target) {
    $target.each(function () {
      const domStyle = $(this).attr("style");
      if (!domStyle) {
        return;
      }
      if (domStyle.search(/background.*.#666/) >= 0 || domStyle.search(/background.*.#333/) >= 0) {
        $(this).css({"background-color": "#ddd"});
      } else if (domStyle.search(/background.*.#111/) >= 0) {
        $(this).css({"background-color": "#fff"});
      } else if (domStyle.search(/border.*.#111/) >= 0) {
        $(this).css({"border-color": "#fff"});
      }
    });
  }
}

function setMarsSearch() {
  let el = document.createElement("script");
  /*
		if( is_index() ){
			el.src = './asset/js/ext/sug.js#sv=//mf2ap005.marsflag.com/mf2/vsearch_honda__om__om';
		}else{
			el.src = '../asset/js/ext/sug.js#sv=//mf2ap005.marsflag.com/mf2/vsearch_honda__om__om';
		}
		*/
  /* 2023.02.14 */
  el.src = "https://ce.mf.marsflag.com/latest/js/mf-search.js";
  document.body.appendChild(el);

  $("#search input.b").on("click", function (e) {
    e.preventDefault();
    makeSearchWord();
  });
}

function makeSearchWord() {
  let original_phrase = $("#search input#MF_form_phrase").val();

  original_phrase = original_phrase.replace(MANUAL_NAME, "");
  original_phrase = original_phrase.replace(MANUAL_YEAR, "");

  let phrase = original_phrase + " " + MANUAL_NAME + " " + MANUAL_YEAR;
  $("#search input#MF_form_phrase").val(phrase);
  $("#search form").submit();
  $("#search input#MF_form_phrase").val(original_phrase);
}

function getPath(str) {
  setSlick;
  //if( !is_main() && !is_visual() ){
  if (is_index()) {
    return str.replace(/\.\.\//g, "./");
  } else {
    return str;
  }
}
function getRoot(str) {
  if (!is_index()) {
    return "../" + str;
  } else {
    return str;
  }
}
function clearEmptyTag() {
  $("span").each(function () {
    if ($(this).html() == "") {
      $(this).hide();
    }
  });
}

function setGlobalNav() {
  $("#searchNav").on("click", function () {
    if ($("#search").css("display") === "block") {
      $("#search").slideUp(100);
    } else {
      $("#search").slideDown(200);
    }
  });
  $("#tabNav").on("click", function () {
    if ($("body").hasClass("status-nav")) {
      $("body").removeClass("status-nav");
      $(".bg-shadow").removeClass("is-show");
    } else {
      $("body").addClass("status-nav");
      $(".bg-shadow").addClass("is-show");
    }
  });
  $(".bg-shadow").on("click", function () {
    $("body").removeClass("status-nav");
    $(this).removeClass("is-show");
  });
}

function setPageIndex() {
  if ($(".page-index").length > 0 && $(".lamp_list").length > 0) {
    $(".lamp_list p").each(function () {
      //console.log( $(this).find('a').attr('href') );
      const $a = $(this).find("a");
      if ($a.attr("href").indexOf("details") < 0) {
        let url = "./details/" + $a.attr("href");
        $a.attr("href", url);
        const $img = $a.find("img");
        let src = $img.attr("src");
        $img.attr("src", src.replace("../", "./"));
      }
    });
  }
}

function setLayout() {
  //タイトルの位置を、ページトップへ移動
  $(".main").prepend($(".title").eq(0));

  const getHeader = function () {
    // let header = getPath('<div class="wrapper"><a href="../index.html" id="om"><img src="../asset/images/mark.png" alt="Owners Manual"></a><div id="tabNav" class=""><img src="../asset/images/icon_nav.png" alt=""></div><div id="siteTitle">' + MANUAL_NAME + '</div><div id="searchNav"><img src="../asset/images/icon_search_big.png" alt=""></div><div id="search"><div class="inner"><form action="//nvsearch.honda.co.jp/om/search.x"><input type="search" name="q" id="MF_form_phrase" autocomplete="off" class="tf" value="" placeholder="Search"><input type="submit" value="" class="b"><input type="hidden" name="ie" value="utf8"></form></div></div></div>');

    // 2023.02.14
    let header = getPath(
      '<div class="wrapper"><a href="../index.html" id="om"><img src="../asset/images/mark.png" alt="Owners Manual"></a><div id="tabNav" class=""><img src="../asset/images/icon_nav.png" alt=""></div><div id="siteTitle">' +
        MANUAL_NAME +
        "</div>" +
        '<div class="mf_finder_container"><mf-search-box submit-text="" ajax-url="https://finder.api.mf.marsflag.com/api/v1/finder_service/documents/3249e001/search" serp-url="/ownersmanual/webom/jpn/search/index.html#/" imgsize-default=0 doctype-hidden category-hidden sort-hidden pagemax-hidden imgsize-hidden options-hidden placeholder="取扱説明書内を検索"></mf-search-box> </div>'
    );

    return header;
  };
  const getFooter = function () {
    let footer = getPath('<div id="footer"><div class="wrapper"><div class="inner"><a href="/" target="_blank"><img src="../asset/images/logo.png" id="Honda" alt="Honda" /></a>');
    let manualtop = '<a href="../../../../../HondaMotor/auto/" id="ownersManual" target="_blank">取扱説明書トップ</a></div></div></div>';
    if (is_index()) {
      footer += manualtop.replace("../../../../../", "../../../../");
    } else {
      footer += manualtop;
    }

    return footer;
  };
  const $screen = $("<div>").addClass("layout-screen");
  const $header = $("<div>").addClass("layout-header").append(getHeader());
  const $container = $("<div>").addClass("layout-container");
  const $main = $("<div>").addClass("layout-main");
  const $side = $("<div>").addClass("nav-side");
  const $footer = $("<div>").addClass("layout-footer").append(getFooter());
  const $wrap = $(".wrap");
  $main.append($wrap);
  $("body").append($screen);

  /*
		if( location.pathname.indexOf('toclist.html') >= 0 ){
			$container.append( $main );
		}else{
			$container.append( $main, $side );
		}	
		*/
  $container.append($main, $side);

  //$container.append( $main, $side );
  $screen.append($header, $container, $footer);

  $(".layout-container").append($("<div>").addClass("bg-shadow"));

  //$('body').css({'opacity': 1});
}

// 2025.05.14 mars search filter
function setSearchFilter() {
  const existingInput = document.querySelector('input[name="d"]');
  if (existingInput) {
    existingInput.remove();
  }

  const form = document.querySelector(".mf_finder_searchBox_form");
  const hiddenInput = document.createElement("input");
  hiddenInput.type = "hidden";
  hiddenInput.name = "d";
  hiddenInput.value = SEARCH_FILTER_WORD;
  form.appendChild(hiddenInput);
}
function checkHref() {
  const path = location.pathname;
  if (path.indexOf("detailsnavi") >= 0) {
    $(".main a.light.mainlink").each(function () {
      let href = $(this).attr("href");
      $(this).attr({href: "../detail/" + href});
    });
  } else if (path.indexOf("detail") >= 0 /*&& path.indexOf('visual') >= 0*/) {
    $(".main a.light.navilink").each(function () {
      let href = $(this).attr("href");
      $(this).attr({href: "../detailsnavi/" + href});
    });
  }
}

function loadSide(obj) {
  /*
			obj.json
			obj.$target
			obj.className
			obj.callback
		*/
  const json_url = obj.json;
  const className = obj.className;
  const $target = obj.$target;
  const callback = obj.callback;
  const detailsDir = obj.detailsDir;

  $.ajax({
    url: json_url,
    type: "GET",
    dataType: "json",
  })
  .done(function (data) {
    let $ul = $("<ul>").addClass(className);
    let url = "";
    let navList = [];

    let cList = data.ContentsList;
    navList = cList.filter(function (val, idx, self) {
      const nameList = self.map((val) => val["HTMLtemplate"]);
      if (nameList.indexOf(val.HTMLtemplate) === idx) {
        return val;
      }
    });

    $.each(navList, function (idx, v) {
      //L1
      if ($ul.children("li:last-child").children(".listtitle").text() != v.L1) {
        let $li = $("<li>");
        let $title = $("<div>").addClass("listtitle").html(v.L1);
        let $child_ul = $("<ul>").addClass("-L1");
        $li.append($title, $child_ul);
        $ul.append($li);
      }

      //L2
      if ($ul.children("li:last-child").children(" .-L1").children("li:last-child").children(".listtitle").text() != v.L2 && $ul.children("li:last-child").children(" .-L1").children("li:last-child").children(".listtitle").html() != v.L2) {
        let $li = $("<li>");
        let $title = $("<div>").addClass("listtitle").html(v.L2);
        let $child_ul = $("<ul>").addClass("-L2");
        $li.append($title, $child_ul);
        //console.log($ul.children('li:last-child'))
        $ul.children("li:last-child").children(".-L1").append($li);
      }

      //L3
      if ($ul.children("li:last-child").children(" .-L1").children("li:last-child").find(".-L2").children("li:last-child").children(".menu").text() != v.L3) {
        let $li = $("<li>");
        let url = "";

        if (is_index()) {
          url = v.HTMLtemplate.replace("./contents/HTMLtemplate/", detailsDir.replace("../", "./"));
        } else if (is_visual()) {
          url = v.HTMLtemplate.replace("./contents/HTMLtemplate/", detailsDir);
        } else {
          url = v.HTMLtemplate.replace("./contents/HTMLtemplate/", detailsDir);
        }

        let $menu = $("<a>").addClass("menu light").html(v.L3).attr({href: url});

        $li.append($menu);
        if (v.L2 == "") {
          $ul.children("li:last-child").children(".-L1").append($li);
        } else {
          $ul.children("li:last-child").children(" .-L1").children("li:last-child").find(".-L2").append($li);
        }
      }
    });

    $target.append($ul);
    $("body").addClass("nav-loaded");

    setMenuAcordion();
    setMenuCurrent();

    if (callback) {
      callback();
    }

    return $ul;
  })
  .fail(function (data) {
    // error
    //console.log('error');
  });

  const setMenuAcordion = function () {
    //console.log($('.listtitle'));
    $(".nav-side .listtitle").on("click", function () {
      const $myLi = $(this).closest("li");
      if ($myLi.hasClass("-current")) {
        $myLi.children("ul").slideUp(100, function () {
          $myLi.removeClass("-current");
        });
      } else {
        $myLi.children("ul").slideDown(300, function () {
          $myLi.addClass("-current");
        });
      }
    });
  };

  const setMenuCurrent = function () {
    const pathname = location.pathname;
    const list = pathname.split("/");
    const targetURL = list[list.length - 1];
    if (!targetURL) {
      return;
    }
    $(".nav-side a").each(function () {
      const url = $(this).attr("href");

      if (pathname.indexOf("lamp_detail") >= 0 && url.indexOf("lamp") >= 0) {
        $(this).closest("ul").parents("li").addClass("-current");
      } else if (url.indexOf(targetURL) >= 0) {
        if (pathname.indexOf("details/qalist.html") >= 0 && url.indexOf("navi-qalist.html") >= 0) {
          return;
        }
        $(this).closest("ul").parents("li").addClass("-current");
        $(this).addClass("-this");
      }
    });
  };
}

function setSlick() {
  if ($(".slider").length > 0) {
    $(".slider").on("init", function () {
      $(".slider").css({height: "auto"}).hide().slideDown(300);
      $("body").addClass("is-sliderloaded");
    });
    var $slider = $(".slider").slick({
      dots: false,
      infinite: true,
      speed: 500,
      fade: false,
      //cssEase: 'linear'
    });
    //$slider.css("max-width", 500 )
  }
}

function setContainerMore() {
  $(".container-more dt").on("click", function () {
    const $next = $(this).next();
    if ($next.css("display") === "block") {
      $next.slideUp(100);
      $(this).removeClass("-current");
      $next.removeClass("-current");
    } else {
      $next.slideDown(200);
      $(this).addClass("-current");
      $next.addClass("-current");
    }
  });
}

// レスポンシブ対応として5列以上のテーブルに対しscrollxクラスを追加　240423saiki
var tables = document.querySelectorAll("table");

function addScrollxToTableWrap() {
  var tables = document.querySelectorAll(".table-wrap table");

  tables.forEach(function (table) {
    var headerRows = table.querySelectorAll("thead tr");
    var maxCols = 0;

    headerRows.forEach(function (row) {
      var cells = row.cells;
      var colCount = 0;
      Array.from(cells).forEach(function (cell) {
        var colspan = cell.getAttribute("colspan") || 1;
        colCount += parseInt(colspan, 10);
      });

      if (colCount > maxCols) {
        maxCols = colCount;
      }
    });

    if (maxCols >= 5) {
      var parentDiv = table.closest(".table-wrap");
      if (parentDiv) {
        parentDiv.classList.add("scrollx");
      }
    }
  });
}

// olタグの2桁判別（2024/04/30追加）
function addClassForDoubleDigit() {
  // 全てのolタグを取得
  const olElements = document.querySelectorAll("ol.procedure");

  olElements.forEach((ol) => {
    // olタグのスタート値を取得（デフォルトは1）
    const startValue = parseInt(ol.getAttribute("start")) || 1;

    // liタグの総数を取得
    const liCount = ol.querySelectorAll("li").length;

    // 開始値 + liタグの数 - 1 で最終の数字が算出
    const finalNumber = startValue + liCount - 1;

    // 最終の数字が2桁以上であれば、digit2クラスを追加
    if (finalNumber >= 10) {
      ol.classList.add("digit2");
    }
  });
}

function changePosErrorList() {
  if ($(".error_message_wrap").length >= 0) {
    $(".error_list").each(function (idx) {
      //console.log($('.error_message_wrap > .title').eq( idx ));
      $(".error_message_wrap > .title").eq(idx).after($(this));
    });
  }
}

function initTocList($ul) {
  let el = document.createElement("script");
  el.src = "../asset/js/masonry.pkgd.min.js";
  document.head.appendChild(el);
  $("#tocListDiv").append($ul);

  //20220527
  if (HAS_NAVI) {
    if ($("#tocListDiv > .-L1").length > 0) {
      $("#tocListDiv > .-L1").insertAfter($("#tocListDiv .listtitle.of-navi"));
    }
  }

  $ul.find(".listtitle.of-banner01").closest("li").remove();

  setTimeout(function () {
    $(".layout-main .root > li > ul").masonry({
      //itemSelector: 'li',
      columnWidth: ".root li",
      horizontalOrder: true,
    });
  }, 1200);
}
function scrollByHash() {
  if (is_visual()) {
    return;
  }

  if (location.hash) {
    if ($(location.hash).length == 0) {
      return;
    }

    let targetY = $(location.hash).offset().top;

    const offsetY = 40;
    let y = targetY - $(".layout-header").outerHeight() - offsetY;
    let marginTop = parseInt($(location.hash).css("margin-top"));

    if (marginTop !== 0) {
      y += marginTop;
    }
    setTimeout(function () {
      $("html, body").animate({scrollTop: y}, 500);
    }, 300);
  }

  $('a[href*="#"]').on("click", function (e) {
    const offsetY = 40;
    const speed = 400;
    let href = $(this).attr("href");
    if (location.pathname.indexOf(href) >= 0) {
      e.preventDefault();
    }
    let hash_list = href.split("#");
    let $target = $("#" + hash_list[hash_list.length - 1]);
    let position = $target.offset().top - $(".layout-header").outerHeight() - offsetY;
    $("body,html").animate({scrollTop: position}, speed, "swing");
    return false;
  });
}

function is_index() {
  if (location.pathname == MANUAL_PATH || location.pathname == MANUAL_PATH + "index.html" || location.pathname == MANUAL_PATH + "index2.html") {
    return true;
  } else {
    return false;
  }
}

function is_visual() {
  if (location.pathname.indexOf("visual") >= 0) {
    return true;
  } else {
    return false;
  }
}

function is_main() {
  if (location.pathname.indexOf("detailsnavi") >= 0) {
    return false;
  } else if (location.pathname.indexOf("details") >= 0) {
    return true;
  } else {
    return false;
  }
}
function is_navi() {
  if (location.pathname.indexOf("detailsnavi") >= 0) {
    return true;
  } else {
    return false;
  }
}
function is_toclist() {
  if (location.pathname.indexOf("toclist.html") >= 0) {
    return true;
  } else {
    return false;
  }
}

function getDeviceFromUA() {
  var ua = navigator.userAgent;
  if (ua.indexOf("iPhone") > 0 || ua.indexOf("iPod") > 0 || (ua.indexOf("Android") > 0 && ua.indexOf("Mobile") > 0)) {
    return _DEVICE_SP;
  } else if (ua.indexOf("iPad") > 0 || ua.indexOf("Android") > 0) {
    return _DEVICE_TAB;
  } else {
    return _DEVICE_PC;
  }
}

function checkQAUrl() {
  $(".nav-side .root a").each(function () {
    let href = $(this).attr("href");
    if (href.indexOf("qalist.html") >= 0) {
      console.log(href);
    }
  });
}

function showPopBookmark() {
  if (!is_index() || getDeviceFromUA() !== _DEVICE_SP) {
    return;
  }

  window.setTimeout(function () {
    var bubble = new google.bookmarkbubble.Bubble();

    //storage.clear();
    //var parameter = 'bmb=1';
    var parameter = "#";

    bubble.hasHashParameter = function () {
      //return window.location.hash.indexOf(parameter) != -1;
      return location.hash == "" && location.href.indexOf(parameter) == location.href.length - 1;
    };

    bubble.setHashParameter = function () {
      if (!this.hasHashParameter()) {
        //window.location.hash = parameter;
        location.href = parameter;
      }
    };

    bubble.getViewportHeight = function () {
      window.console.log("Example of how to override getViewportHeight.");
      return window.innerHeight;
    };

    bubble.getViewportScrollY = function () {
      window.console.log("Example of how to override getViewportScrollY.");
      return window.pageYOffset;
    };

    bubble.registerScrollHandler = function (handler) {
      window.console.log("Example of how to override registerScrollHandler.");
      window.addEventListener("scroll", handler, false);
    };

    bubble.deregisterScrollHandler = function (handler) {
      window.console.log("Example of how to override deregisterScrollHandler.");
      window.removeEventListener("scroll", handler, false);
    };

    var result = bubble.showIfAllowed();

    //2025.05.14 storage change
    var storage = localStorage;
    if (!result) {
      // 期限チェック
      var expire = JSON.parse(localStorage.getItem("expire"));
      if (expire) {
        dateString = expire;
        now = new Date().getTime();
        if (now > dateString) {
          storage.removeItem("BOOKMARK_DISMISSED_COUNT");
        }
      } else {
        var day = 1; // 1日
        var nmsec = day * 1000 * 60 * 60 * 24;
        localStorage.setItem("expire", new Date().getTime() + nmsec);
      }
    }
    // var storage = localStorage;
    // storage.clear();
    // if( !result ){
    // 	//add
    // 	var expire = JSON.parse(localStorage.getItem("expire"));
    // 	if( expire ){
    // 		dateString = expire;
    // 		now = new Date().getTime();
    // 		if( now > dateString ){
    // 			storage.clear();
    // 		}
    // 	}else{
    // 		var day = 1; //1day
    // 		var nmsec = day * 1000 * 60 * 60 * 24;
    // 		localStorage.setItem("expire", new Date().getTime() + nmsec );
    // 	}
    // }
  }, 1000);
}

//20240603saiki”no-before”を追加する処理
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".L5 .lower-title.no_accordion").forEach(function (element) {
    var nextElement = element.nextElementSibling;
    if (nextElement && (nextElement.classList.contains("custom") || nextElement.classList.contains("custom_item"))) {
      // Remove ::before pseudo-element by adding a class
      element.classList.add("no-before");
    }
  });
});
function agreement() {
  let cValue = "true";
  const cancelMessage = "使用承諾書および個人情報使用同意書をキャンセルしますか？";
  const agreementFile = "agreement.html";
  const savepath = "/ownersmanual/";
  const PLATFOMRS = [
    "Y!J-SRD",
    "Y!J-MBS/1.0",
    "Yahoo! Slurp",
    "Yahoo! DE Slurp",
    "Googlebot-Mobile/",
    "Googlebot/",
    "adsence-Google",
    "msnbot",
    "bingbot/",
    "Hatena",
    "MicroAd/",
    "Baidu",
    "MJ12bo",
    "Steeler",
    "YodaoBot",
    "OutfoxBot",
    "Pockey",
    "psbot",
    "Yeti/",
    "Websi",
    "Wget/",
    "NaverBot",
    "BecomeBot",
    "heritr",
    "DotBot",
    "Twiceler",
    "ichiro",
    "archive.org_bot",
    "YandexBot/",
    "ICC-Crawler",
    "SiteBot/",
    "TurnitinBot/",
    "Purebot/",
  ];

  let $agreement = $("<div>").addClass("agreement-wrap");

  if (isAlreadyAgreed() === true) {
    return;
  }
  if (window.MF_CAPTURE) {
    //2022.08.02
    return true;
  }
  if (isCrawler() === true) {
    return;
  }

  $("body").prepend($agreement);

  $.ajax({
    type: "GET",
    url: getRoot(agreementFile),
    //dataType: "text",
    success: function (data) {
      $agreement.html(data);

      setShowAgreement();
    },
    error: function () {
      $agreement.html("読み込みに失敗しました");
    },
  });

  function setShowAgreement() {
    $agreement.find(".container").hide().slideDown();
    $("body").addClass("is-agree");

    // キャンセルボタン
    $agreement.find("#submitCancel").click(function (e) {
      e.preventDefault();
      history.back();
    });

    $agreement.find("#submitAgree").click(function (e) {
      e.preventDefault();
      //2025.05.14
      //$.cookie( getKey( MANUAL_PATH ), cValue, { path: savepath, expire:""} )
      //2026.01.06 Cookie secure対策
//$.cookie( getKey(), cValue, { path: savepath, expire:""} );
$.cookie(
	getKey(),
	cValue,
	{
		path: savepath,
		expires: "",
		secure: true,
		sameSite: 'Lax'
	}
)
      $agreement.fadeOut(300, function () {
        callback();
      });
      $("body").removeClass("is-agree");
    });
  }

  function isAlreadyAgreed() {
    //2025.05.14
    //var key = getKey( MANUAL_PATH );
    var key = getKey(COOKIE_AGREEMENT);
    if ($.cookie(key) === "true") {
      return true;
    }
    return false;
  }

  function isCrawler() {
    var userAgent = window.navigator.userAgent;

    if (userAgent == "") {
      return true;
    }
    for (var i = 0; i < PLATFOMRS.length; i++) {
      var Platform = PLATFOMRS[i];
      if (userAgent.indexOf(Platform) >= 0) {
        return true;
      }
    }
  }

  function getKey(str) {
    //2025.05.14
    return COOKIE_AGREEMENT;
    //return str.replace( /\//g , '');
  }
}

/*! jquery.cookie v1.4.1 | MIT */
!(function (a) {
  "function" == typeof define && define.amd ? define(["jquery"], a) : "object" == typeof exports ? a(require("jquery")) : a(jQuery);
})(function (a) {
  function b(a) {
    return h.raw ? a : encodeURIComponent(a);
  }
  function c(a) {
    return h.raw ? a : decodeURIComponent(a);
  }
  function d(a) {
    return b(h.json ? JSON.stringify(a) : String(a));
  }
  function e(a) {
    0 === a.indexOf('"') && (a = a.slice(1, -1).replace(/\\"/g, '"').replace(/\\\\/g, "\\"));
    try {
      return (a = decodeURIComponent(a.replace(g, " "))), h.json ? JSON.parse(a) : a;
    } catch (b) {}
  }
  function f(b, c) {
    var d = h.raw ? b : e(b);
    return a.isFunction(c) ? c(d) : d;
  }
  var g = /\+/g,
    h = (a.cookie = function (e, g, i) {
      if (void 0 !== g && !a.isFunction(g)) {
        if (((i = a.extend({}, h.defaults, i)), "number" == typeof i.expires)) {
          var j = i.expires,
            k = (i.expires = new Date());
          k.setTime(+k + 864e5 * j);
        }
        return (document.cookie = [b(e), "=", d(g), i.expires ? "; expires=" + i.expires.toUTCString() : "", i.path ? "; path=" + i.path : "", i.domain ? "; domain=" + i.domain : "", i.secure ? "; secure" : ""].join(""));
      }
      for (var l = e ? void 0 : {}, m = document.cookie ? document.cookie.split("; ") : [], n = 0, o = m.length; o > n; n++) {
        var p = m[n].split("="),
          q = c(p.shift()),
          r = p.join("=");
        if (e && e === q) {
          l = f(r, g);
          break;
        }
        e || void 0 === (r = f(r)) || (l[q] = r);
      }
      return l;
    });
  (h.defaults = {}),
    (a.removeCookie = function (b, c) {
      return void 0 === a.cookie(b) ? !1 : (a.cookie(b, "", a.extend({}, c, {expires: -1})), !a.cookie(b));
    });
});
