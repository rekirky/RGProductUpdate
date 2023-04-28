function myFunction() {
	var input, filter, ul, li, a, i, txtValue;
	input = document.getElementById('myInput');
	filter = input.value.toUpperCase();
	ul = document.getElementById('myUL');
	li = ul.getElementsByTagName('li');
	for (i = 0; i < li.length; i++) {
		a = li[i].getElementsByTagName('a')[0];
		txtValue = a.textContent || a.innerText;
		if (txtValue.toUpperCase().indexOf(filter) > -1) {
			li[i].style.display = '';
		} else {
			li[i].style.display = 'none';
		}
	}
}
function myFilter() {
	var input, filter, ul, li, a, i, txtValue;
	input = document.getElementById('myYear');
	filter = input.value.toUpperCase();
	ul = document.getElementById('myUL');
	li = ul.getElementsByTagName('li');
	for (i = 0; i < li.length; i++) {
		a = li[i].getElementsByTagName('span')[0];
		txtValue = a.textContent || a.innerText;
		if (txtValue.toUpperCase().indexOf(filter) > -1) {
			li[i].style.display = '';
		} else {
			li[i].style.display = 'none';
		}
	}
}
function filterResults() {
	var input1, input2, filter1, filter2, ul, li, a, i, txtValue;
	input1 = document.getElementById('myInput');
	input2 = document.getElementById('myYear');
	filter1 = input1.value.toUpperCase();
	filter2 = input2.value.toUpperCase();
	ul = document.getElementById('myUL');
	li = ul.getElementsByTagName('li');
	for (i = 0; i < li.length; i++) {
		a = li[i].getElementsByTagName('a')[0];
		txtValue = a.textContent || a.innerText;
		if (txtValue.toUpperCase().indexOf(filter1) > -1 &&
			li[i].getElementsByTagName('span')[0].textContent.toUpperCase().indexOf(filter2) > -1) {
			li[i].style.display = '';
		} else {
			li[i].style.display = 'none';
		}
	}
}