# Embedding

Projects hosted on Compute Studio can be embedded as an [`iframe`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe) on any website. Once you've published your project, send me an email at [hank@compute.studio](mailto:hank@compute.studio). I'll generate a special embed link for your project. [^embed]


Next, embed the link on the target website with code like this. Take care to replace the example `title` and `src` values with your own:

```html
<iframe
id="cs-iframe"
title="Test Iframe"
scrolling="no"
src="https://compute.studio/hdoupe/dash-demo/embed/app/"
></iframe>
```

## Set up Iframe-resizer (optional)

Compute Studio uses the [Iframe-resizer](https://github.com/davidjbradshaw/iframe-resizer) library to dynamically resize your embedded project so that it loads responsively for all screen sizes. This requires a few extra steps:

1. Install the content script in your project's static assets: [`iframeResizer.contentWindow.min.js`](https://raw.githubusercontent.com/davidjbradshaw/iframe-resizer/master/js/iframeResizer.contentWindow.min.js)

2. Go to the "Configure" tab in your project's settings on Compute studio and make sure **Use Iframe Resizer** is checked:

    ![Embed docs](https://user-images.githubusercontent.com/9206065/122590340-6c109b00-d02f-11eb-94a2-ab465ed68e6a.png)

3. On your website, add the controller script from `iframe-resizer`: [`iframeResizer.min.js`](https://raw.githubusercontent.com/davidjbradshaw/iframe-resizer/master/js/iframeResizer.min.js)

    Then add this CSS:

    ```css
    iframe.cs-iframe {
      min-width: 100%;
    }
    ```

    And, this Javascript:

    ```html
    <script type="text/javascript" src="/assets/iframeResizer.min.js"></script>
    <script>
        iFrameResize({ log: false, heightCalculationMethod: 'lowestElement' }, '#cs-iframe');
    </script>
    ```

For more information about Iframe-resizer, checkout the [docs](http://davidjbradshaw.github.io/iframe-resizer/#typical-setup).


[^embed]: This link is only good for one domain. This restriction prevents other people from using your data visualization on their website without your permission. If you need to embed it on multiple websites, then I'll generate a link for each one.
