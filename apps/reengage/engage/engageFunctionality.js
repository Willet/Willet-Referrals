var postQueue = new Array(); //The queue of posts to be made
var contentFormat = ["TypeA", "TypeB", "TypeC"];
var postID = 0; //Each post is given a unique ID based on the order they were made

//Post object declaration
function Post(title, content, typeOfContent, contentLink, id) {
	this.title = title; //Title of post - only seen in Engage, not on FB
	this.content = content; //Content of the FB post
	this.typeOfContent = typeOfContent; //User selects from a choice
	this.contentLink = contentLink;
	this.ID = id; //Currently id is only used for deleting objects
	
	//Extremely basic error checking (currently not in use)
	this.checkForErrors = function() {
		var errors = "";
		if (typeof title === 'undefined' || title === "") {
			errors += "title ";
		}
		if (typeof content === 'undefined' || content === "") {
			errors += "content ";
		}
		if(typeof typeOfContent === 'undefined') {
			errors += "type of content ";
		}
		
		return errors;
	}
}

function createNewPost(inputTitle, inputFirst) {
	var title = inputTitle;
	var first = inputFirst;
	
	var content = "";
	var typeOfContent = "";
	var contentLink = "";
	
	var newPost = new Post(title, content, typeOfContent, contentLink, postID++);
	if (first === "First") {
		postQueue.splice(0,0,newPost);
	}
	else if (first === "Last") {
		postQueue.push(newPost);
	}
}

function writeQueue() { //Outputs post titles and dates in replaceWithPosts, aka main box area
	var out = "";
	
	//If no posts in queue, suggest making a new post, else write out the posts in the queue
	if (postQueue.length === 0) {
		out += "<div id='replaceWithPosts'><div id='replaceTextWithPosts'>";
		out += "<p>Make a new Facebook post by clicking the 'New Post' button!<br><br>";
		out += "The posts you create here will be seen by any of your visitors who 'liked' a product.</p></div></div>";
	}
	else {
		out += "<div id='replaceWithPosts'>";
		for (i = 0; i < postQueue.length; i++) {
			var post = postQueue[i];
			out += "	<a href='#'><div class='post' id='"+post.ID+"'>";
			out += "		<div class='postDate'>"+getDate(i)+"</div>";
			out += "		<div class='postTitle'>"+post.title+"</div></a>";
			out += "		<a href='#'><div class='postDelete' title='"+post.ID+"'><img id='delete"+post.ID+"' src='imgs/delete-norm-15x15.png'></div></a>";
			out += "	</div>";
		}
		out += "</div>";
	}
	
	$("#replaceWithPosts").replaceWith(out);
}

function removePost(id) { //Looks through queue for post of this id and deletes it
	var q = confirm("Are you sure you want to delete this post?");
	
	if (q) {
		var x = 0;
		for (i = 0; i < postQueue.length; i++) {
			if (postQueue[i].ID === id) {
				postQueue.splice(i, 1);
				
				if (postQueue.length > 0) { //If queue isn't empty
					if (postQueue.length === 1) x = postQueue[0].ID; //If queue only has one post left in it
					else if (postQueue.length === i) x = postQueue[i-1].ID; //If deleted post was last in queue
					else x = postQueue[i].ID;
				}
			}
		}
	
		writeQueue();
		
		if (postQueue.length > 0) $("#"+x).addClass("selected");
		else ("#selectedTitle").replaceWith("<div id='selectedTitle'>Post Title Here</div>");
	}
}

function clickPost(post) {
	var content = post.content;
	var id = post.ID;
	var typeOfContent = post.typeOfContent;
	
	$(".post").removeClass("selected");  // remove active class from all posts
    $("#"+id).addClass("selected");      // add active class to clicked element
	
	var out = "";
	
	out += "	<div id='replaceWithPostContent' class='roundedBR'>";
	out += "		<div id='postContentContainer'>";
	out += "			<div id='postKind'>";
	out += "				What kind of content is this?";
	out += "				<select id='postKind'>";
	out += "					<option value='type1' {{ ifType1 }}>Type 1</option>";
	out += "					<option value='type2' {{ ifType2 }}>Type 2</option>";
	out += "					<option value='type3' {{ ifType3 }}>Type 3</option>";
	out += "				</select>";
	out += "				<br><br> Facebook post content:";
	out += "			</div>";
	out += "			<div id='postGuts'>";
	out += "				<textarea width='100%' rows='4' id='postContent'>"+content+"</textarea>";
	out += "			</div>";
	out += "			<div id='postEmbed'>";
	out += "				<input type='button' value='Embed a photo or video' />";
	out += "			</div><br><br>";
	out += "			<div id='postSave' title='"+post.ID+"'><a href='#'><div class='button'>";
	out += "				Save Changes";
	out += "			</div></a></div>";
	out += "		</div>";
	out += "	</div>";
	
	//If typeOfContent is equal to typei, then make typei selected
	for (i = 1; i < 4; i++) {
		var selected = (typeOfContent === 'type'+i) ? "selected='selected'" : "";
		out = out.replace('{{ ifType'+i+' }}', selected);
	}
	
	//return out;
	$("#replaceWithPostContent").replaceWith(out);
	
	var postTitle = "<div id='selectedTitle'>"+post.title+" (<a href='#'><span id='editTitle'>edit</span></a>)</div>";
	$("#selectedTitle").replaceWith(postTitle);
}

$(document).ready(function() {

	//Debug purposes - indicates feature not made yet
	$(function() {
		$(".comingSoon").live("click", function() {
			alert("Coming soon!");
		});
	});
	
	//When 'New Post' is clicked
	$(function() {
		$("#newPost").live("click", function() {
			//make sure that currently selected post was given content, that is, if queue.length > 0
			//also make sure changes from current post were saved
			
			if (postQueue.length === 0) document.getElementById("light").style.display='block';
			else {
				var id = $(".post.selected").attr('id');
				for (i = 0; i < postQueue.length; i++) {
					if (postQueue[i].ID == id) var post = postQueue[i];
				}
				
				if (post.content !== $("#postContent").val() || post.typeOfContent !== $("#postKind option:selected").val()) {
					var q = confirm("Unsaved changes. Discard changes?");
					if (q) {
						$("#postContent").val(post.content);
						if ($("#postContent").val() === "") alert("Give your current post some content first!");
						else if (q) document.getElementById("light").style.display='block';
					}
				}
				else if (post.content === "") alert("Give your current post some content first!");
				else document.getElementById("light").style.display='block';
			}
		});
	});
	
	//When 'cancel' in 'new post' dialog is clicked
	$(function() {
		$("#newPostCancel").live("click", function() {
			document.getElementById("light").style.display='none';
			$("#newPostTitle").val("");
		});
	});
	
	//When 'ok' in 'new post' dialog is clicked
	$(function() {
		$("#newPostOk").live("click", function() {
			var title = $("#newPostTitle").val();
			var first = $('input[name=first]:checked').val();
			
			//Make sure a title was given to the new post
			if (title === "") alert("Give your post a title!");
			else {
				//Create post, make lightbox disappear, update queue
				createNewPost(title, first);
				document.getElementById("light").style.display='none';
		
				writeQueue();
	
				//Write queue, select newly created post
				if (first === "First") {
					var id = postQueue[0].ID;
					var post = postQueue[0];
				}
				else if (first === "Last") {
					var id = postQueue[postQueue.length - 1].ID;
					var post = postQueue[postQueue.length - 1];
				}
				
				post.typeOfContent = "type1" //This is the default value - change later
			
				clickPost(post);
				$("#newPostTitle").val("");
			}
		});
	});

	//When a post is clicked, clickPost() populates post content to right, and selects the clicked post
	//First checks to make sure you've saved any changes to the right
	$(function() {
	    $(".post").live("click", function() {
	    	//newID is id of post just clicked, oldId is id of post previously selected
    	    var newId = $(this).attr('id');
        	var oldId = $(".post.selected").attr('id');
        
	        for (i = 0; i < postQueue.length; i++) {
    	    	if (oldId == postQueue[i].ID) {
        			var oldPost = postQueue[i];
        		}
        	}
       	 
       		for (i = 0; i < postQueue.length; i++) {
        		if (newId == postQueue[i].ID) {
        			var newPost = postQueue[i];
        			
        			if (postQueue.length > 1) {
        				var typeOfContent = $("#postKind option:selected").val();
						var content = $("#postContent").val();
						if (oldPost.content === "" && content === "") {
							alert("Give your post some content!");
						}
        				else if ((oldPost.typeOfContent != typeOfContent) || (oldPost.content != content)) {
        					var q = confirm("You have unsaved changes. Discard changes?");
        					if (q) {
        						$("#postContent").val(oldPost.content);
        						if (oldPost.content !== "") clickPost(newPost);
        						else alert("Give your current post some content first!");
        					}
        				}
        				else clickPost(newPost);
       				}
					else clickPost(newPost);
        		}
        	}
    	});
	});
	
	//Delete post hover and click actions
	$(function() {
		$(".postDelete").live({
			mouseenter: function() {
				var id = $(this).attr("title");
				$("#delete"+id).attr("src", "imgs/delete-hov-15x15.png");
			},
			mouseleave: function() {
				var id = $(this).attr("title");
				$("#delete"+id).attr("src", "imgs/delete-norm-15x15.png");
			},
			click: function() {
				var id = $(this).attr("title");
				var q = confirm("Are you sure you want to delete this post "+id+"?");
		
				if (q) {
					var x = 0;
					for (i = 0; i < postQueue.length; i++) {
						if (id == postQueue[i].ID) {
							postQueue.splice(i, 1);
					
							if (postQueue.length > 0) { //If queue isn't empty
								if (postQueue.length === 1) x = 0; //If queue only has one post left in it
								else if (postQueue.length === i) x = i - 1; //If deleted post was last in queue
								else x = i;
							}
						}
					}
			
					writeQueue();
			
					//If there are posts remaining, select post identified by var x in above looping; otherwise remove post content form
					if (postQueue.length > 0) {
						alert("Post id "+postQueue[x].ID+" should now be selected");
						clickPost(postQueue[x]);
					}
					else {
						var out = "<div id='replaceTextWithPostContent'><p>Selected Facebook post contents will appear here</p></div>";
						$("#postContentContainer").replaceWith(out);
						
						var postTitle = "<div id='selectedTitle'>Post Title Here</div>";
						$("#selectedTitle").replaceWith(postTitle);
					}
				}
			}
		});
	});
		
	//When you click 'save', contents are saved to the post
	$(function() {
		$("#postSave").live("click", function() {
			if ($("#postContent").val() === "") alert("Give your post some content!");
			else {
				var id = $(this).attr("title");
				var post = "";
				for (i = 0; i < postQueue.length; i++) {
					if (id == postQueue[i].ID) {
						post = postQueue[i];
					}
				}
				
				post.typeOfContent = $("#postKind option:selected").val();
				post.content = document.getElementById('postContent').value;
				
				alert("Saved!");
			}
		});
	});
	
	//When you click 'edit' beside the title, prompts you to change the post title
	$(function() {
		$("#editTitle").live("click", function() {
			var newTitle = prompt("Enter a new title for your post:");
			while (newTitle === "") {
				if (newTitle === "") alert("You can't give a post an empty title! Try again");
				var newTitle = prompt("Enter a new title for your post:");
			}
			
			if (newTitle !== null) {
				var id = $(".post.selected").attr('id');
				for (i = 0; i < postQueue.length; i++) {
					if (postQueue[i].ID == id) {
						var post = postQueue[i];
					}
				}
				post.title = newTitle;
				var postTitle = "<div id='selectedTitle'>"+post.title+" (<a href='#'><span id='editTitle'>edit</span></a>)</div>";
				$("#selectedTitle").replaceWith(postTitle);
			}
		});
	});

});

/*DOMAIN/r/shopify/queue/GET(param)

$.ajax({
url: "",
data: {
    "shop": ....
    "content":
},
method: "GET",
callback:  function(response) {
}
})*/

function getDate(x) {
	//For now set to be every MWF
	
	var month = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
	var monthDays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
	
	//The days to set 
	var currentTime = new Date();
	var setMonth = currentTime.getMonth();
	var setDay = currentTime.getDate(); 
	var day = currentTime.getDay(); //Day of the week, 0 = Sunday etc - therefore posts made on 1, 3, 5
	var year = currentTime.getYear();
	
	
	if (day === 0 || day === 2 || day === 4) {
		incDay(1);
	}
	else if (day === 6) {
		incday(2);
	}
	
	for (i = 0; i < x; i++) { //Run for loops for x intervals of time
		if ( day === 1 || day === 3) {
			incDay(2);
		}
		else if (day === 5) {
			incDay(3);
		}
	}
	
	//incDay makes sure days weeks and months are incremented appropriately (eg there's no 13th month)
	function incDay(x) {
		day = (day + x) % 7;
		
		if ( (setDay + x) < monthDays[setMonth] ) {
			setDay += x;
		}
		else {
			setDay = ( (setDay + x) % monthDays[setMonth] );
			if (setMonth < 11) { //If month isn't Dec, go to next month
				setMonth++;
			} 
			else { //If month is Dec, set to Jan
				setMonth = 0;
				year++;
				
				//Change days in February depending on year
				if ( (year % 4 === 0) && (year % 100 !== 0) ) {
					monthDays[1] = 29;
				}
				else {
					monthDays[1] = 28;
				}
			}
		}
	}
	
	//returns "(Month) (Day)" eg "January 11"
	return month[setMonth] + " " + setDay;
}
