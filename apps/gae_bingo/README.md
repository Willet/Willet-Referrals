# GAE/Bingo

GAE/Bingo is a drop-in split testing framework for App Engine, built for [Khan Academy](http://www.khanacademy.org) and *heavily* modeled after [Patrick McKenzie](http://www.kalzumeus.com)'s [A/Bingo](http://www.bingocardcreator.com/abingo). If you're on App Engine, GAE/Bingo can get your A/B tests up and running in minutes.

You can read [more about the initial inspiration and design of
GAE/Bingo](http://bjk5.com/post/10171483254/a-bingo-split-testing-now-on-app-engine-built-for-khan).

* <a href="#features">Features</a>  
* <a href="#screens">Experiment Dashboard</a>
* <a href="#bare">Bare Minimum Example</a>
* <a href="#usage">Usage and Code Samples</a>  
* <a href="#principles">Design Principles</a>  
* <a href="#start">Getting Started</a>  
* <a href="#non-features">Non-features so far</a>  
* <a href="#bonus">Bonus</a>  
* <a href="#faq">FAQ</a>  

## <a name="features">Features</a>

Free features [inherited quite directly from A/Bingo's design](http://www.bingocardcreator.com/abingo) (imagine quotes around the following):

* Test display or behavioral differences in one line of code.
* Measure any event as a conversion in one line of code.
* Eliminate guesswork: automatically test for statistical significance.
* Blazingly fast, with minimal impact on page load times or server load.
* Written by programmers, for programmers. Marketing is an engineering discipline!

Plus some stuff to satisfy Khan Academy's needs:

* Drop into App Engine with minimal configuration
* Framework agnostic -- works with webapp, Django, Flask, whatever.
* Persistent storage of test results -- if you're running experiments
  that take a long time like, say, [testing your software's effects on a student's education](http://www.khanacademy.org), that's no problem.
* Performance optimized for App Engine

## <a name="screens">Experiment Dashboard</a>

<img src="http://i.imgur.com/x4Hew.png"/><br/>

Your dashboard, available at `/gae_bingo/dashboard`, lets you control all experiments and provides statistical analysis of results.</em>

## <a name="bare">Bare Minimum Example</a>

These two lines of code calling the `ab_test` and `bingo` functions are all you need to start A/B testing.

<pre>from gae_bingo.gae_bingo import ab_test, bingo

# Start an ab_test, returning True or False
use_new_button_design = ab_test("new button design"):

#...then, when ready to score a conversion...
bingo("new button design")
</pre>

That's it! You're split-testing your users, with consistent behavior per-user, automatic statistical tracking, and more. If you want more power, read on.

## <a name="usage">Usage and Code Samples</a>

  * <a href="#starting">Starting an experiment</a>
  * <a href="#scoring">Scoring a conversion</a>
  * <a href="#specifying">Specifying alternatives</a>
  * <a href="#multiple">Multiple conversion types</a>
  * <a href="#testing">Testing your alternatives</a>
  * <a href="#controlling">Controlling and ending your experiments</a>

### <a name="starting">Starting an experiment</a>
This line of code will automatically set up an A/B test named "new button
design" (the first time only) and return True or False. Use this anywhere
you can run Python code, it's highly optimized.

<pre>from gae_bingo.gae_bingo import ab_test

...

if ab_test("new button design"):
    return "new_button_class"
else:
    return "old_button_class"
</pre>

You can also specify an identifier for the conversion metric you're expecting
to analyze.

<pre>
if ab_test("crazy new type of animal", conversion_name="animals escaped"):
    return Gorillas()
else:
    return Monkeys()
</pre>

If you don't specify a conversion_name when starting a test, GAE/Bingo will
automatically listen for conversions with the same name as the experiment.

### <a name="scoring">Scoring a conversion</a>
This line of code will score a conversion in the "new button design" experiment
for the current user.

<pre>from gae_bingo.gae_bingo import bingo

...
bingo("new button design")
</pre>

...or, in the case of the above "crazy new type of animal" experiment,
<pre>bingo("animals escaped")
</pre>

### <a name="specifying">Specifying alternatives</a>
Even though the above two lines are all you need to start running some pretty
useful A/B tests, you've got more power than that. Choose from any of the
following lines of code to return various alternatives for your tests.
Remember: each individual user will get consistent results from these
functions.

<pre>from gae_bingo.gae_bingo import ab_test

...

# SIMPLE
#
# Returns True or False
#
use_new_button_design = ab_test("new button design")

...

# LIST OF ALTERNATIVES
#
# Returns "old" or "shiny"
#
button_class = ab_test("new button class", ["old", "shiny"])

...

# LIST OF >2 ALTERNATIVES (multivariate testing)
#
# Returns 10, 15, or 20
#
answers_required = ab_test("answers required", [10, 15, 20])

...

# WEIGHTED ALTERNATIVES
# (use a dictionary with alternatives as keys and weights as values)
#
# Returns "crazy" to 1/5 of your users and "normal" to 4/5 of your users
#
crazy_experiment = ab_test("crazy experiment", {"crazy": 1, "normal": 4})

</pre>

### <a name="multiple">Analyzing multiple types of results for a single experiment</a>
You may want to statistically examine different dimensions of an experiment's
effects. You can do this by passing an array to the conversion_name parameter.

<pre>
breed_new_animal = ab_test("breed new animal", conversion_name=["animals escaped", "talking animals"])
</pre>

This syntactic sugar will automatically create multiple experiments for you.
Your conversions will be tracked independently with their own statistical
analysis, so you can independently call bingo() when appropriate:

<pre>
bingo("animals escaped")
</pre>

...and...

<pre>
bingo("talking animals")
</pre>

This lets you monitor your experiment's statistical effects on both escaping and talking animals, separately, via the dashboard.

### <a name="testing">Testing your alternatives ahead of time</a>
If you're on the dev server and wanna take a look-see at how your various
alternatives behave before you ship 'em, you can override the current request's
selection of A/B alternatives by adding the `gae_bingo_alternative_number`
request param, like so: `?gae_bingo_alternative_number=2`

### <a name="controlling">Controlling and ending your experiments</a>
Typically, ending an experiment will go something like this:

1. You'll check out your dashboard at `/gae_bingo/dashboard`
1. You'll notice a clear experiment winner and click "End experiment, picking this" on the dashboard. All users will now see your chosen alternative.  
2. You'll go into the code and remove your old ab_test() call, replacing it w/ the clear winner.  
3. You'll delete the experiment from the dashboard if you no longer need its historical record.

## <a name="principles">Design Principles</a>

Just go read through [Patrick McKenzie's slides on A/B testing design principles](http://www.bingocardcreator.com/abingo/design). This implementation only tweaks those to achieve:

* Persistence to datastore for very-long-lasting records and very-long-running
  experiments without sacrificing performance.
* Quick to drop-in for any App Engine (Python) developer, with
  strong-but-customizable ties to existing App Engine user identities.

## <a name="start">Getting Started</a>

1. Download this repository's source and copy the `gae_bingo/` folder into your App Engine project's root directory.

2. Add the following handler definitions (found in `yaml/app.yaml`) to your app's `app.yaml`:
<pre>
handlers:
&ndash; url: /gae_bingo/static
&nbsp;&nbsp;static_dir: gae_bingo/static<br/>
&ndash; url: /gae_bingo/tests/.*
&nbsp;&nbsp;script: gae_bingo/tests/main.py<br/>
&ndash; url: /gae_bingo/.*
&nbsp;&nbsp;script: gae_bingo/main.py
</pre>
...and the following job definitions (found in `yaml/cron.yaml`) to your app's `cron.yaml`:
<pre>
cron:
&ndash; description: persist gae bingo experiments to datastore
&nbsp;&nbsp;url: /gae_bingo/persist
&nbsp;&nbsp;schedule: every 5 minutes
</pre>

3. Modify the WSGI application you want to A/B test by wrapping it with the gae_bingo WSGI middleware:
<pre>
&#35; Example of existing application
application = webapp.WSGIApplication(...existing application...)<br/>
&#35; Add the following
from gae_bingo.middleware import GAEBingoWSGIMiddleware
application = GAEBingoWSGIMiddleware(application)
</pre>

4. (Optional, suggested) If you want, modify the contents of config.py to match your application's usage. There
   are two functions to modify: can_control_experiments() and
   current_logged_in_identity()
<pre>
\# Customize can_see_experiments however you want to specify
\# whether or not the currently-logged-in user has access
\# to the experiment dashboard.
\#
def can_control_experiments():
&nbsp;&nbsp;&nbsp;&nbsp;\# This default implementation will be fine for most
&nbsp;&nbsp;&nbsp;&nbsp;return users.is_current_user_admin()
</pre><br/>
<pre>
\# Customize current_logged_in_identity to make your a/b sessions
\# stickier and more persistent per user.
\#
\# This should return one of the following:
\#
\#   A) a db.Model that identifies the current user, something like models.UserData.current()
\#   B) a unique string that consistently identifies the current user, like users.get_current_user().user_id()
\#   C) None, if your app has no way of identifying the current user for the current request. In this case gae_bingo will automatically use a random unique identifier.
\#
def current_logged_in_identity():
&nbsp;&nbsp;&nbsp;&nbsp;return users.get_current_user().user_id() if users.get_current_user() else None
</pre><br/>
If you want the most consistent A/B results for users who are anonymous and
then proceed to login to your app, you should have this function return
a db.Model that inherits from models.GaeBingoIdentityModel. Example: `class UserData(GAEBingoIdentityModel, db.Model):`<br/>
...GAE/Bingo will take care of the rest.

5. You're all set! Start creating and converting A/B tests [as described
   above](#usage).

## <a name="non-features">Non-features (well, some of them)</a>

In order to get v1 out the door, a number of features were cut. Please feel
free to help us accomplish the following:

* Multivariate statistical analysis -- currently we only automatically analyze
  experiments w/ exactly 2 alternatives.
* Multiple participation in experiments -- currently each user is only counted
  once per experiment.
* Nicer bot detection -- we took the cheap and quick route of checking user
  agents for bots even thought testing for javascript execution is much more
  effective. This shouldn't screw w/ your statistical analysis, conversions
  look rarer than they actually are due to bots getting through the filter.

## <a name="bonus">Bonus</a>

GAE/Bingo is currently in production use at [Khan Academy](http://khanacademy.org). If you make good use of it elsewhere, be sure to let us know so we can brag about you to others (ben@khanacademy.org).

## <a name="faq">FAQ</a>

1. Would you have been able to build any of this without [A/Bingo](http://www.bingocardcreator.com/abingo)'s lead to
   follow?

    Nope.

2. Shouldn't I just be using Google Website Optimizer or some other
   javascript-powered A/B testing framework?

    [I'll let Patrick handle this one](http://www.bingocardcreator.com/abingo/compare).

3. How come you didn't just use one of the existing Python split testing
   frameworks like django-lean?

    django-lean is awesome, but we strongly believe in a couple of the core
    principles of A/Bingo, particularly making it as ridiculously easy as
    possible for developers (and anybody else) to create A/B tests. We couldn't find
    a framework that satisfied our needs, so we decided to spread the A/Bingo love.

    We also wanted this to quickly drop into any App Engine app, and we didn't want to
    exclude those on App Engine who aren't using Django.

4. Can I use this framework for my iguana website?

    It's all yours. GAE/Bingo is [MIT licensed](http://en.wikipedia.org/wiki/MIT_License).

5. Did you design the dashboard template?

    Nope -- check out https://github.com/pilu/web-app-theme
