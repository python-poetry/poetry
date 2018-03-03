from ..elements.array import ArrayElement
from .errors import ParsingError
from .tokenstream import TokenStream


class Capturer:
    """
    Recursive-descent matching DSL. Yeah..
    """

    def __init__(self, token_stream, value=tuple(), dormant_error=None):
        self._token_stream = token_stream
        self._value = value
        self._dormant_error = dormant_error

    def find(self, finder):
        """
        Searches the token stream using the given finder.

        `finder(ts)` is a function that accepts a `TokenStream` instance and returns `(element, pending_ts)`
        where `element` is the found "something" or a sequence of "somethings", and `pending_ts` the unconsumed
        `TokenStream`.

        `finder(ts)` can raise `ParsingError` to indicate that it couldn't find anything, or
        a `TokenStream.EndOfStream` to indicate a premature end of the TokenStream.

        This method returns a Capturer instance that can be further used to find more and more "somethings". The value
        at any given moment can be retrieved via the `Capturer.value()` method.
        """

        try:

            # Execute finder!
            element, pending_ts = finder(self._token_stream)

            # If result is not a sequence, make it so
            if isinstance(element, ArrayElement) or not isinstance(element, (tuple, list)):
                element = (element,)

            # Return a Capturer with accumulated findings
            return Capturer(pending_ts, value=self.value() + element)

        except ParsingError as e:

            # Failed to find, store error in returned value
            return Capturer(self._token_stream, dormant_error=e)

        except TokenStream.EndOfStream as e:

            # Premature end of stream, store error in returned value
            return Capturer(self._token_stream, dormant_error=e)

    def value(self, parsing_expectation_msg=None):
        """
        Returns the accumulated values found as a sequence of values, or raises an encountered dormant error.

        If parsing_expectation_msg is specified and a dormant_error is a ParsingError, the expectation message is used
        instead in it.
        """

        if self._dormant_error:
            if parsing_expectation_msg and isinstance(self._dormant_error, ParsingError):
                raise ParsingError(parsing_expectation_msg, token=self._token_stream.head)
            else:
                raise self._dormant_error
        return self._value

    @property
    def pending_tokens(self):
        """
        Returns a TokenStream with the pending tokens yet to be processed.
        """
        return self._token_stream

    def or_find(self, finder):
        """
        If a dormant_error is present, try this new finder instead. If not, does nothing.
        """
        if self._dormant_error:
            return Capturer(self._token_stream).find(finder)
        else:
            return self

    def or_end_of_file(self):
        """
        Discards any errors if at end of the stream.
        """
        if isinstance(self._dormant_error, TokenStream.EndOfStream):
            return Capturer(self.pending_tokens, value=self._value)
        else:
            return self

    def or_empty(self):
        """
        Discards any previously-encountered dormant error.
        """
        if self._dormant_error:
            return Capturer(self.pending_tokens, value=self._value)
        else:
            return self

    def and_find(self, finder):
        """
        Accumulate new "somethings" to the stored value using the given finder.
        """

        if self._dormant_error:
            return Capturer(self.pending_tokens, dormant_error=self._dormant_error)

        return Capturer(self.pending_tokens, self.value()).find(finder)


def capture_from(token_stream):
    return Capturer(token_stream)

