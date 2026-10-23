$(function(){
if($('#guide').length > 0){

	var is_lock = false;
	var speed = 300;
	var waitTime = 500;
	$(window).load(function(){
		initGuide();
	});
	
	initGuide = function(){
		var initLeft = $('div.root ul li').parent().width();
		$('div.root ul li').css( {'left': initLeft } ).animate({ 'left':0 },　speed * 1.5 );
		$('#prev').hide();
	}

	$('#guide span.answer').click(function(){
		$('#prev').show();
		var nextQuestion = $(this).data('value');
		$(this).addClass('selected');
		var notSelected = $(this).closest('li').siblings();
		notSelected.animate({ 'left':-$(this).parent().width() },speed * 0.6 ,function(){
			goNext( nextQuestion, $(this) );
		});
	});

	var goNext = function( nextQuestion, notSelected )
	{
		$('#' + nextQuestion ).addClass('done').delay( waitTime ).slideDown( speed, 'swing', function(){
			notSelected.delay( waitTime * 0.3 ).slideUp( speed, 'swing' ,function(){ $(this).hide() });
		});
	}
	
	var goPrev = function()
	{
		var lastOne = $('#guide div.done').last();
		if(!lastOne.hasClass('root')){
			lastOne.removeClass('done');
			lastOne.slideUp(speed *0.5, function(){
				var lastChild = $('#guide div.done').last();
				var lis = lastChild.find('li')
				lis.find('span').removeClass('selected');
				lis.slideDown().delay( waitTime * 0.2 ).animate({ 'left':0 }, speed *0.5,function(){
					if($('#guide div.done').last().hasClass('root')){ $('#prev').hide(); }
				});
			});
		}
	}
	$('#prev').click(function(){
		goPrev();
	});

//
}
});