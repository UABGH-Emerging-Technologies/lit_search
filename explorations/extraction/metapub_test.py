import os
os.environ['NCBI_API_KEY']="5c7b745fcba4a835c311c056f725c6814208"
import metapub
from urllib.request import urlretrieve

#  this method uses local caching with no option to disable. 
# metapub has lots of other hard-coded configs as well. 
# So I want to shy away from this -RM


pmid = '38365899'

url = metapub.FindIt(pmid).url

print(url)

final_pdf = f'{pmid}.pdf'

urlretrieve(url, final_pdf)

# with open(final_pdf, "w") as textfile:
#     textfile.write(textract.process(
#         tmp_txt,
#         extension='pdf',
#         method='pdftotext',
#         encoding="utf_8",
#     ))