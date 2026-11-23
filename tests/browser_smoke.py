"""Exercise real retained RFC metadata at a Pages project subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil,tempfile,threading
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
def main():
 screenshots=ROOT/'browser-checks';screenshots.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as temp:
  shutil.copytree(ROOT/'dist',Path(temp)/'example-tool');server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temp));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/example-tool/');expect(page.locator('#record-title')).to_have_text('HTTP Semantics',timeout=20000)
    page.locator('#query').fill('2324');expect(page.locator('#result-count')).to_have_text('1 matching RFCs');page.locator('#results button').click();expect(page.locator('#record-number')).to_have_text('RFC 2324')
    with page.expect_download() as download:page.locator('#save').click()
    assert download.value.suggested_filename=='rfc-2324-trail.json'
    page.locator('#query').fill('9110');page.locator('#results button').click();page.locator('#relations button',has_text='RFC 7231').click();expect(page.locator('#record-number')).to_have_text('RFC 7231')
    page.locator('#depth').select_option('2');expect(page.locator('#trail-status')).to_contain_text('relationships')
    page.locator('#query').fill('<img src=x onerror=alert(1)>');expect(page.locator('#empty')).to_be_visible();assert page.locator('img').count()==0
    page.locator('#clear').click()
    with page.expect_download() as download:page.locator('#export').click()
    assert download.value.suggested_filename=='rfc-trail-results.csv'
    page.screenshot(path=str(screenshots/'desktop.png'),full_page=True);page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),page.evaluate('({page:document.documentElement.scrollWidth,viewport:innerWidth})');page.screenshot(path=str(screenshots/'mobile.png'),full_page=True);assert not errors,errors;browser.close()
   print('Browser checks passed: full capture, arbitrary RFC, relationships, exports and mobile')
  finally:server.shutdown()
if __name__=='__main__':main()
