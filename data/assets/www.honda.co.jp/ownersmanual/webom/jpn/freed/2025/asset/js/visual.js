/* visual */

	const SCENE_WIDTH = 950;
	const SCENE_HEIGHT = 468;
	let $POP = '';
	let inlineJson = '';
	let index = 0;

	//////////////////////////////////////////////////////////


	window.addEventListener('load', function() {

		$POP = $('.pop-link');
		//int
		$('body').addClass('is-visualloaded');


		initEvent();
		loadData();
	

	});

	$(window).resize(function() {
	  setPosMark();
	  setPosZoom();
	  setPopLinkPos();
	});

	//////////////////////////////////////////////////////////


	function setPopLinkPos(){
		if( $(window).width() <= 500 ){
			if( $('.visual-index > .pop-link').length == 0){
				$('.visual-index').append($('.pop-link'));
			}
		}else{
			if( $('.visual-index .main .pop-link').length == 0){
				$('.visual-index .main').append($('.pop-link'));
			}
		}
	}

	function initEvent(){

		$('[data-scene]').on('click' ,function(e){

				const targetid = $(this).data('scene');
				const id = '#' + targetid;
				changeScene( id );
				closePop();
				subScene();
				//history.pushState( {'scene':id} , null, id );

		});	
		$('.scene').on('click' ,function(){
				closePop();
		});


		//history.pushState( {'scene':location.hash} , null, location.hash );
		//console.log(history.state)

    window.addEventListener('popstate', function(e) {
    	//console.log(history.state)
    	//if (!e.originalEvent.state) return; 
    	//if( history.state == null ){return;}
      changeScene(location.hash);


    });
	}

	function subScene(){
		$('.subScene').removeClass('-show');
	}

	function changeScene( targetId ){
		 const mytargetId = targetId.replace('#', '');
		 $('.scene ').hide().css( {'opacity':0});
		 $POP.hide();

		 $( targetId ).show().one().animate( {'opacity':1}, 100, function(){
				setPosMark();
				setPosZoom();
				
				$('.panel li').removeClass('-current');
				$('[data-scene="'+ mytargetId +'"]').addClass('-current');
		 });

		 $(window).scrollTop(0);
		 location.hash = mytargetId;


	}

	function loadData(){
		const path_json = '../language/ja_JP/main/json/visualindex_content.json';
		$.ajax({
	    url: path_json,
	    type: 'GET',
	    dataType: "json",
	  }).done(function ( pointdata) {
	  	const path_json = '../language/ja_JP/main/json/inline.json';
			$.ajax({
		    url: path_json,
		    type: 'GET',
		    dataType: "json",
		  }).done(function (data) {
		  	inlineJson = data;
		  	makeScene( pointdata['ja-JP']['nodes'] );
		  	
		  	if( location.hash ){
		  		changeScene( location.hash );
		  	}else{
		  		changeScene( '#out_front_id' );
		  	}
		  }).fail(function (data) {
		    // error
		    //console.log('error');
		  });

	  }).fail(function (data) {
	    // error
	    //console.log('error');
	  });
	}

	function makeScene( data ){
		$.each( data, function( idx, val ){
			//val.id
			const sceneId = val.id;
			$.each( val.nodes, function( idx, v ){
				if( v.type === 'point' ){
					setPoint( v , sceneId );
				}else if( v.type === 'zoom' ){
					setZoomNav( v , sceneId  );
				}
			});
		});
		
		setPosZoom();
		setPosMark();
	}

	function setZoomNav( v , sceneId ){
		//console.log(v)
		
		const zoomId = v.id;
		const nodes = v.nodes;
		const bgImg = v.img;
		const $zoom = $('<div>').addClass('zoom');

		$.each( v.possize.split(';'), function( idx, val ){
				//console.log(val);
				if( val ){		
					let myval = '';
					if( val.indexOf('right') >= 0 ){
						myval = val.replace('right:' ,'');
						$zoom.attr( 'data-right', Math.round( (parseInt(myval) / SCENE_WIDTH)  * 1000 ) / 1000 );
					}else if( val.indexOf('width') >= 0 ){
						myval = val.replace('width:' ,'');
						$zoom.attr( 'data-width', Math.round( (parseInt(myval) / SCENE_WIDTH)  * 1000 ) / 1000 );
					}else if( val.indexOf('height') >= 0 ){
						myval = val.replace('height:' ,'');
						$zoom.attr( 'data-height', Math.round( (parseInt(myval) / SCENE_HEIGHT)  * 1000 ) / 1000 );
					}else if( val.indexOf('top') >= 0 ){
						myval = val.replace('top:' ,'');
						$zoom.attr( 'data-top', Math.round( (parseInt(myval) / SCENE_HEIGHT)  * 1000 ) / 1000 );
					}
				}
		});

		$zoom.on('click',function(e){
			$( '#' + zoomId ).addClass('-show');
		});

		$( '#' + sceneId ).append( $zoom ) ;
		setZoomScene( sceneId, zoomId, v , bgImg );
	}

	function setPoint( v , sceneId ){
		if( v.type == "zoom" ){
			//console.log( v.nodes  )
			return;
		}
		if( !v.nodes  ){
			return;	
		}
		const $point = $('<div>').addClass('point');


		$point.attr( 'data-bottom', (parseInt(v.bottom) / SCENE_HEIGHT)  );
		$point.attr( 'data-right',  (parseInt(v.right) / SCENE_WIDTH) );

		let dataLink = '[';
		let count = v.nodes.length;
		$.each( v.nodes, function( idx, val ){

			let content = (val.content).replace( /'/g, '"').replace( /..\/..\//g, '');
			//console.log(content);
			/*
			let buf = val.content.match(/\t\(\w+\)/g);
			if( buf ){
				$.each(buf,function( i, v ){
					const id = buf[i].match(/\w+/)[0];
					const $icon = getIconImg( getInlineIconObj( id ) ) ;
					content = content.replace( buf[i] , $icon[0].outerHTML );
				});
			}else{
				content = val.content;
			}
			*/

			if(val.is_navi){
				//console.log(val.link);
			}
			
			if( val.link ){
				dataLink += "{";
				dataLink += "'content':'" + content + "' , 'link':'" + val.link + "'";
				if(val.is_navi){
					dataLink += ",'is_navi': true";
				}
				dataLink += "}";
			}else if( val.type ){
				dataLink += "{'content':'" + content + "' , 'type':'" + val.type + "'}";
			}

			if( count - 1 > idx ){
				dataLink += ',';
			}
		});
		dataLink += ']';
		$point.attr( 'data-link', dataLink );

		$point.on('click', function(e){
			e.stopPropagation();
			if( $(this).hasClass('-current') ){
				closePop();
				return;
			}
			$point.removeClass('-current');
			$POP.find( 'li' ).remove();
			
			let x = $(this).position().left;
			let y = $(this).position().top;
			const w = $(this).width();
			const offsetX = 20;
			const offsetY = 20;

			setPopList( $(this).attr('data-link') );

			if( x + $POP.width()/2 > $('.scene').width() ){
				x = $('.scene').width() - $POP.width()/2 - offsetX;
			}else if( x -  $POP.width()/2  < 0 ){
				x = $POP.width()/2;
			}

			if( y + w  + offsetY + $POP.height()  > $('.scene').height() ){
				y = y - w*2 - $POP.height() ;
			}
			$POP.css({ 'top': y + w  + offsetY  , 'left': x + w/2  }).slideDown( 150 );
			$('.point').removeClass('-current');
			$(this).addClass('-current');
			$('body').addClass('has-popup');
		});
		$( '#' + sceneId  ).append( $point ) ;
	}

	function getInlineIconObj( id ){
		return inlineJson['ja-JP'].nodes.find((v) => v.id == id);
	}
	function getIconImg( obj ){
		let $img = $('<img>').attr({ 'src': obj.content,'style': obj.style}).addClass('icon');
		return $img;
	}

	function setPosMark(){
		const w = $('.main').width() ;
		const h = $('.main').height();

		$('.point').each(function(){
			const right = w * $(this).attr('data-right');
			let bottom = h * $(this).attr('data-bottom');
			if( bottom + $(this).height() > h ){
				bottom = h - $(this).height();
			}else if( bottom < $(this).height() ){
				//bottom = $(this).height();
			}

			//console.log(bottom);
			$(this).css({ 'right': right + 'px','bottom': bottom + 'px' });
		});
	}

	function setPosZoom(){
		const w = $('.scene').width() ;
		const h = $('.scene').height();

		$('.zoom').each(function(){
			const right = w * $(this).attr('data-right') ;
			let top = h * $(this).attr('data-top');
			const width = w * $(this).attr('data-width');
			const height = h * $(this).attr('data-height');
			if( top + height > h){
				top = h - height;
			}
			$(this).css({ 'right': right+ 'px','top': top+ 'px', 'width': width + 'px'  ,'height': height + 'px' });
		});
	}

	function closePop(){
		$POP.hide();
		$POP.find( 'li' ).remove();
		$('body').removeClass('has-popup');
		$('.point').removeClass('-current');
	}

	function setPopList( list ){
		$.each( eval(list) , function( idx, val ){
			if( val.link ){
				let link;
				if( val.is_navi ){
					link = val.link.replace('../../../HTMLtemplate/','../detailsnavi/');
				}else{
					link = val.link.replace('../../../HTMLtemplate/','../details/');
				}
				
				let $a = $('<a>').attr( 'href',link ).html( val.content ).addClass('label');
				$POP.children('ul').append( $('<li>').append( $a ) );
				$a.on('click', function(){
					$POP.hide();
					$('.point').removeClass('-current');
				})
			}else if( val.type ){
				//console.log( val.content );
				let $div = $('<div>').addClass('label -type').html( val.content );
				$POP.children('ul').append( $('<li>').append( $div ) );
			}
		});
	}

	function setZoomScene( sceneId , zoomId , data , img ){
		const $img = $('<img>').attr('src', '../asset/images/visual_blank.png').css({'background-image': 'url(' +img.replace('../../', '')+ ')'  }).addClass('pic');
		const $subScene = $('<div>').addClass('subScene').attr('id',zoomId );
		const $type = $('<div>').addClass('type');
		const $close = $('<div>').addClass('close').on('click', function(){
			$(this).closest('.subScene').removeClass('-show');
		});
		$subScene.append( $close );
		$subScene.append( $img );

		$( '#' + sceneId ).append( $subScene ) ;
		
		$.each( data.nodes, function( idx, v ){
			if( v.type === 'point' ){
				setPoint( v , zoomId );
			}else if( v.type === 'zoompoint' ){
				setZoomNav( v , zoomId  );
			}else if( v.type === 'label' ){
				$subScene.prepend( $type.html(v.content));
			}
		});
	}


