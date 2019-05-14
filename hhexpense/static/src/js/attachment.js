function _onAttachmentViewPdf(self){
    console.log('you are in attachment pdf part');
    var path = self.nextElementSibling.href;
    path = path.replace('?download=1','');
    console.log(path);
    window.open(path);
}

function _onAttachmentViewImg(self){
    console.log('you are in attachment view part');
    var path = self.src;
    console.log(path);
    window.open(path);
}






