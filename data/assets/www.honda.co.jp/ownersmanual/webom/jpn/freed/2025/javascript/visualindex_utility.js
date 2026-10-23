var json_vi_content="";

function setpopup(slang, url, isTop) {
	//2020.03.02 他言語対応
	slang = getLaunguage("en-GB");

    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true); // JSON読み込み
    xhr.send("");
    xhr.onloadend = function () {
        // JSON読み込み後の処理
        json_vi_content = JSON_parse2(xhr.responseText);

        setpopup_2(slang, isTop);
    }

   /*$.ajax({
	  "url":url,
	  "success":function(data){

	     json_vi_content = data;
		 
	     setpopup_2(slang, isTop);
	   }
	})*/
}

function setpopup_2(slang, isTop) {

	//2020.03.02　他言語対応
	slang = getLaunguage("en-GB");

	var jso = json_vi_content[slang];
	
	// TODO:わかりやすさ重視　速度向上の余地あり　後でやる
    //var level = jso.level;
    var imgDir = "../img/";
    var htmlDir = "./";
    
    if (isTop)
	{
		imgDir = "../../../img/";
		htmlDir = "../../../HTMLtemplate/";
	}
	
    if(jso.nodes)
    {
    	for (var i = 0; i < jso.nodes.length; i++)
        {
        	var pos= jso.nodes[i].pos;
        	var id = jso.nodes[i].id;
        	var vijso = jso.nodes[i];
        	
            var target = document.getElementById(id);
            
            if(target)
        	{
        		if(vijso)
        		{
        			var buf=''
        		    for (var j = 0; j < vijso.nodes.length; j++)
        		    {
        		    	var type = vijso.nodes[j].type;
        		    	var point_id = vijso.nodes[j].id;
        		    	var possize = vijso.nodes[j].possize;
        		    	
        		    	if(type=="point")
        		    	{
	        		    	var point_right = vijso.nodes[j].right;
	        		    	var point_bottom = vijso.nodes[j].bottom;
	        		    	
	        		    	buf = buf + "<p class=\"point_off " + point_id +  "\" style=\"right:" + point_right + ";bottom:" + point_bottom + ";\"></p>";
							if(vijso.nodes[j].nodes)
						    {
	                             buf = buf + "<div class=\"pop pop" + point_id.substring(7,5) + "\" style=\"display: none;" + possize + "\">";
	                             
	        		             for (var k= 0; k < vijso.nodes[j].nodes.length; k++)
	        		             {
	        		             	 var link = vijso.nodes[j].nodes[k].link;
	        		             	 var title = vijso.nodes[j].nodes[k].content;
	        		             	 
	                                 buf = buf + "<p><a href=\"" + link + "\" style=\"display: block;\">" + title + "<span></span></a></p>";
	        		             }
	        		             buf = buf + "</div>";
						    }
						}
						else if(type=="zoom")
						{
	        		    	var point_zoom_img = vijso.nodes[j].img;
							buf = buf + "<p class=\"" + point_id +  " area\" style=\"" + possize + ";\"></p>";
							
							buf = buf + "<div class=\"zoomArea zoom" + point_id.substring(6,4)+  " area\" style=\"background-image:url('" + point_zoom_img + "');\">";

							if(vijso.nodes[j].nodes)
						    {
	        		             for (var k= 0; k < vijso.nodes[j].nodes.length; k++)
	        		             {
        		    				var point_id2 = vijso.nodes[j].nodes[k].id;
			        		    	var point_right2 = vijso.nodes[j].nodes[k].right;
			        		    	var point_bottom2 = vijso.nodes[j].nodes[k].bottom;
        		    				var possize2 = vijso.nodes[j].nodes[k].possize;
			        		    	
        		    				var point_type2 = vijso.nodes[j].nodes[k].type;
        		    				
			        		    	if(point_type2=="point"){
								    	buf = buf + "<p class=\"point_off " + point_id2 +  "\" style=\"right:" + point_right2 + ";bottom:" + point_bottom2 + ";\"></p>";
										if(vijso.nodes[j].nodes[k].nodes)
									    {
				                             buf = buf + "<div class=\"pop pop" + point_id2.substring(7,5) + "\" style=\"display: none;" + possize2 + "\">";
				                             
				        		             for (var m = 0; m < vijso.nodes[j].nodes[k].nodes.length; m++)
				        		             {
				        		             	 var link2 = vijso.nodes[j].nodes[k].nodes[m].link;
				        		             	 var title2 = vijso.nodes[j].nodes[k].nodes[m].content;
				        		             	 
				                                 buf = buf + "<p><a href=\"" + link2 + "\">" + title2 + "<span></span></a></p>";
				        		             }
				        		             buf = buf + "</div>";
								        }
							        
							        }
									else if(point_type2=="zoompoint"){
										buf = buf + getZoomPoint(point_id2, possize2, vijso.nodes[j], k, true);
									}
							        
							    }
						    }
						    
							buf = buf + "</div>";
					          //<div class="zoomArea zoom01" style="background-image: url('img/in_zoom_Center.jpg');">
					          //  <p class="point_off point01"></p>
					          //</div>
						}
						else if(type=="zoompoint"){
							buf = buf + getZoomPoint(point_id, possize, vijso, j, false);
						}
        	        }
        			target.innerHTML = buf;
        	    }
        	}
        }
    }
    // ビジュアル検索対応（開始）
    if (isTop) {
        init_visual(); // ビジュアル検索初期設定 (contents_utility.js)
    }
    // ビジュアル検索対応（終了）
}

function getZoomPoint(point_id, possize, vijso, j, isDeep)
{
	var point_zoom_img = vijso.nodes[j].img;
	var buf="";
	buf = buf + "<p class=\"" + point_id +  " zoompoint\" style=\"" + possize + ";\"></p>";
	
	if(isDeep){
	    buf = buf + "<div class=\"zoomAreaDeep " + point_id +  " area deep\" style=\"background-image:url('" + point_zoom_img + "');\">";
    }else{
    	buf = buf + "<div class=\"zoomArea " + point_id +  " area\" style=\"background-image:url('" + point_zoom_img + "');\">";
    }

	// Tomoaki 20210707 Add start
	for (var i = 0; i < vijso.nodes[j].nodes.length; i++) {
		if (vijso.nodes[j].nodes[i].type == "label") {
			if (vijso.nodes[j].nodes[i].content != undefined && vijso.nodes[j].nodes[i].content != null)
				buf = buf + "<p class=\"zoomHighLight\">" + vijso.nodes[j].nodes[i].content + "</p>";
		}
	}
	// Tomoaki 20210707 Add end

    
	if(vijso.nodes[j].nodes)
    {
         for (var k= 0; k < vijso.nodes[j].nodes.length; k++)
		 {
// Tomoaki 20210707 Add start
			 if (vijso.nodes[j].nodes[k].type == "point") {
// Tomoaki 20210707 Add end

				 var point_id2 = vijso.nodes[j].nodes[k].id;
				 var point_right2 = vijso.nodes[j].nodes[k].right;
				 var point_bottom2 = vijso.nodes[j].nodes[k].bottom;
				 var possize2 = vijso.nodes[j].nodes[k].possize;

				 buf = buf + "<p class=\"point_off " + point_id2 + "\" style=\"right:" + point_right2 + ";bottom:" + point_bottom2 + ";\"></p>";
				 if (vijso.nodes[j].nodes[k].nodes) {
					 buf = buf + "<div class=\"pop pop" + point_id2.substring(7, 5) + "\" style=\"display: none;" + possize2 + "\">";

					 for (var m = 0; m < vijso.nodes[j].nodes[k].nodes.length; m++) {
						 var link2 = vijso.nodes[j].nodes[k].nodes[m].link;
						 var title2 = vijso.nodes[j].nodes[k].nodes[m].content;

						 buf = buf + "<p><a href=\"" + link2 + "\">" + title2 + "<span></span></a></p>";
					 }
					 buf = buf + "</div>";
				 }
// Tomoaki 20210707 Add start
			 }
// Tomoaki 20210707 Add end
		 }
    }
    
	buf = buf + "</div>";
	return buf;
}